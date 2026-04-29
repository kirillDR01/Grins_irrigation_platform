"""Unit tests for :class:`WebAuthnService`.

All external dependencies are mocked: Redis, both repositories, AuthService,
and the ``webauthn`` library calls. The goal is to cover the service's
control flow — challenge round-trips, exception mapping, sign-count
regression handling — without standing up a real authenticator.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.exceptions.auth import (
    InvalidCredentialsError,
    WebAuthnChallengeNotFoundError,
    WebAuthnDuplicateCredentialError,
    WebAuthnVerificationError,
)
from grins_platform.services.webauthn_config import WebAuthnSettings
from grins_platform.services.webauthn_service import (
    CHALLENGE_KEY_PREFIX,
    WebAuthnService,
)


def _make_staff() -> MagicMock:
    staff = MagicMock()
    staff.id = uuid4()
    staff.username = "kirill"
    staff.email = "kirill@example.com"
    staff.name = "Kirill Test"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.failed_login_attempts = 0
    staff.locked_until = None
    return staff


def _make_settings() -> WebAuthnSettings:
    return WebAuthnSettings(
        webauthn_rp_id="localhost",
        webauthn_rp_name="Test",
        webauthn_expected_origins="http://localhost:5173",
        webauthn_challenge_ttl_seconds=300,
    )


def _make_service(
    *,
    redis_client: AsyncMock | None = None,
    credential_repo: AsyncMock | None = None,
    user_handle_repo: AsyncMock | None = None,
    staff_repo: AsyncMock | None = None,
    auth_service: MagicMock | None = None,
) -> WebAuthnService:
    return WebAuthnService(
        staff_repository=staff_repo or AsyncMock(),
        credential_repository=credential_repo or AsyncMock(),
        user_handle_repository=user_handle_repo or AsyncMock(),
        auth_service=auth_service or MagicMock(),
        redis_client=redis_client or AsyncMock(),
        settings=_make_settings(),
    )


@pytest.mark.unit
class TestStartRegistration:
    async def test_returns_handle_and_options_and_stores_challenge(self) -> None:
        redis = AsyncMock()
        user_handle_repo = AsyncMock()
        user_handle_repo.get_or_create_for_staff.return_value = b"\x00" * 64
        cred_repo = AsyncMock()
        cred_repo.list_credential_ids_for_staff.return_value = []
        service = _make_service(
            redis_client=redis,
            user_handle_repo=user_handle_repo,
            credential_repo=cred_repo,
        )
        staff = _make_staff()

        with (
            patch(
                "grins_platform.services.webauthn_service.generate_registration_options",
            ) as mock_gen,
            patch(
                "grins_platform.services.webauthn_service.options_to_json_dict",
                return_value={"challenge": "fake"},
            ),
        ):
            mock_gen.return_value.challenge = b"abcd"
            handle, options = await service.start_registration(staff)

        assert isinstance(handle, str) and len(handle) > 16
        assert options == {"challenge": "fake"}
        redis.set.assert_awaited_once()
        # Key shape sanity-check.
        args, _kwargs = redis.set.call_args
        assert args[0].startswith(CHALLENGE_KEY_PREFIX)
        payload = json.loads(args[1])
        assert payload["kind"] == "registration"
        assert payload["staff_id"] == str(staff.id)


@pytest.mark.unit
class TestFinishRegistration:
    async def test_missing_challenge_raises(self) -> None:
        redis = AsyncMock()
        redis.get.return_value = None
        service = _make_service(redis_client=redis)
        with pytest.raises(WebAuthnChallengeNotFoundError):
            await service.finish_registration(
                staff=_make_staff(),
                handle="x",
                credential={},
                device_name="Test",
            )

    async def test_kind_mismatch_raises(self) -> None:
        redis = AsyncMock()
        redis.get.return_value = json.dumps(
            {"kind": "authentication", "challenge": "x", "staff_id": "y"},
        )
        service = _make_service(redis_client=redis)
        with pytest.raises(WebAuthnChallengeNotFoundError):
            await service.finish_registration(
                staff=_make_staff(),
                handle="x",
                credential={},
                device_name="Test",
            )

    async def test_invalid_response_wraps_in_verification_error(self) -> None:
        from webauthn.helpers.exceptions import InvalidRegistrationResponse

        staff = _make_staff()
        redis = AsyncMock()
        redis.get.return_value = json.dumps(
            {
                "kind": "registration",
                "challenge": "AAAA",
                "staff_id": str(staff.id),
            },
        )
        service = _make_service(redis_client=redis)

        with (
            patch(
                "grins_platform.services.webauthn_service.verify_registration_response",
                side_effect=InvalidRegistrationResponse("bad cbor"),
            ),
            pytest.raises(WebAuthnVerificationError),
        ):
            await service.finish_registration(
                staff=staff,
                handle="x",
                credential={"response": {}},
                device_name="Test",
            )

        # Challenge must always be deleted, even on failure.
        redis.delete.assert_awaited()

    async def test_duplicate_credential_raises(self) -> None:
        from webauthn.helpers.structs import CredentialDeviceType

        staff = _make_staff()
        redis = AsyncMock()
        redis.get.return_value = json.dumps(
            {
                "kind": "registration",
                "challenge": "AAAA",
                "staff_id": str(staff.id),
            },
        )
        cred_repo = AsyncMock()
        cred_repo.find_by_credential_id.return_value = MagicMock()
        service = _make_service(redis_client=redis, credential_repo=cred_repo)

        verification = MagicMock()
        verification.credential_id = b"id"
        verification.credential_public_key = b"pk"
        verification.sign_count = 0
        verification.aaguid = "aaa"
        verification.credential_device_type = CredentialDeviceType.SINGLE_DEVICE
        verification.credential_backed_up = False

        with (
            patch(
                "grins_platform.services.webauthn_service.verify_registration_response",
                return_value=verification,
            ),
            pytest.raises(WebAuthnDuplicateCredentialError),
        ):
            await service.finish_registration(
                staff=staff,
                handle="x",
                credential={"response": {"transports": ["internal"]}},
                device_name="Test",
            )


@pytest.mark.unit
class TestFinishAuthentication:
    async def test_missing_credential_raises_verification_error(self) -> None:
        redis = AsyncMock()
        redis.get.return_value = json.dumps(
            {"kind": "authentication", "challenge": "AAAA", "staff_id": None},
        )
        cred_repo = AsyncMock()
        cred_repo.find_by_credential_id.return_value = None
        service = _make_service(redis_client=redis, credential_repo=cred_repo)

        with pytest.raises(WebAuthnVerificationError):
            await service.finish_authentication(
                handle="x",
                credential={"rawId": "AAAA"},
            )

    async def test_disabled_login_raises_invalid_credentials(self) -> None:
        from webauthn.helpers.structs import CredentialDeviceType

        redis = AsyncMock()
        redis.get.return_value = json.dumps(
            {"kind": "authentication", "challenge": "AAAA", "staff_id": None},
        )

        stored_cred = MagicMock()
        stored_cred.credential_id = b"id"
        stored_cred.public_key = b"pk"
        stored_cred.sign_count = 5
        stored_cred.staff_id = uuid4()

        cred_repo = AsyncMock()
        cred_repo.find_by_credential_id.return_value = stored_cred

        staff = _make_staff()
        staff.is_login_enabled = False
        staff_repo = AsyncMock()
        staff_repo.get_by_id.return_value = staff

        auth_service = MagicMock()
        auth_service._is_account_locked.return_value = False

        verification = MagicMock()
        verification.new_sign_count = 6
        verification.credential_device_type = CredentialDeviceType.SINGLE_DEVICE

        service = _make_service(
            redis_client=redis,
            credential_repo=cred_repo,
            staff_repo=staff_repo,
            auth_service=auth_service,
        )

        with (
            patch(
                "grins_platform.services.webauthn_service.verify_authentication_response",
                return_value=verification,
            ),
            pytest.raises(InvalidCredentialsError),
        ):
            await service.finish_authentication(
                handle="x",
                credential={"rawId": "AAAA"},
            )

    async def test_sign_count_regression_revokes_and_raises(self) -> None:
        from webauthn.helpers.structs import CredentialDeviceType

        redis = AsyncMock()
        redis.get.return_value = json.dumps(
            {"kind": "authentication", "challenge": "AAAA", "staff_id": None},
        )

        stored_cred = MagicMock()
        stored_cred.credential_id = b"id"
        stored_cred.public_key = b"pk"
        stored_cred.sign_count = 10
        stored_cred.staff_id = uuid4()

        cred_repo = AsyncMock()
        cred_repo.find_by_credential_id.return_value = stored_cred

        verification = MagicMock()
        verification.new_sign_count = 5  # regression vs stored.sign_count=10
        verification.credential_device_type = CredentialDeviceType.SINGLE_DEVICE

        service = _make_service(redis_client=redis, credential_repo=cred_repo)
        with (
            patch(
                "grins_platform.services.webauthn_service.verify_authentication_response",
                return_value=verification,
            ),
            pytest.raises(WebAuthnVerificationError),
        ):
            await service.finish_authentication(
                handle="x",
                credential={"rawId": "AAAA"},
            )
        # The service decodes "AAAA" (base64url) → b'\x00\x00\x00' before
        # passing it to the repo. The revocation must hit *that* id, not the
        # stored row's id (which the regression check shows is suspect).
        cred_repo.revoke_by_credential_id.assert_awaited_once_with(
            b"\x00\x00\x00",
        )


@pytest.mark.unit
class TestRevokeCredential:
    async def test_not_found_raises(self) -> None:
        from grins_platform.exceptions.auth import (
            WebAuthnCredentialNotFoundError,
        )

        cred_repo = AsyncMock()
        cred_repo.revoke.return_value = False
        service = _make_service(credential_repo=cred_repo)
        with pytest.raises(WebAuthnCredentialNotFoundError):
            await service.revoke_credential(
                credential_row_id=uuid4(),
                staff=_make_staff(),
            )

    async def test_happy_path_returns_none(self) -> None:
        cred_repo = AsyncMock()
        cred_repo.revoke.return_value = True
        service = _make_service(credential_repo=cred_repo)
        result = await service.revoke_credential(
            credential_row_id=uuid4(),
            staff=_make_staff(),
        )
        assert result is None
