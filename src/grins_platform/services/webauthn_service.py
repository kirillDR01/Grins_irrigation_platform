"""WebAuthn / Passkey service.

Owns the four ceremonies (start_registration, finish_registration,
start_authentication, finish_authentication) plus list/revoke. JWT cookie
issuance reuses :class:`AuthService`'s helpers verbatim so passkey login
returns the exact same shape as password login.
"""

from __future__ import annotations

import json
import secrets
from typing import TYPE_CHECKING, Any, ClassVar
from uuid import UUID

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import (
    base64url_to_bytes,
    bytes_to_base64url,
    options_to_json_dict,
)
from webauthn.helpers.exceptions import (
    InvalidAuthenticationResponse,
    InvalidRegistrationResponse,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from grins_platform.exceptions.auth import (
    AccountLockedError,
    InvalidCredentialsError,
    WebAuthnChallengeNotFoundError,
    WebAuthnDuplicateCredentialError,
    WebAuthnVerificationError,
)
from grins_platform.log_config import LoggerMixin

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from grins_platform.models.staff import Staff
    from grins_platform.models.webauthn_credential import WebAuthnCredential
    from grins_platform.repositories.staff_repository import StaffRepository
    from grins_platform.repositories.webauthn_credential_repository import (
        WebAuthnCredentialRepository,
        WebAuthnUserHandleRepository,
    )
    from grins_platform.services.auth_service import AuthService
    from grins_platform.services.webauthn_config import WebAuthnSettings


CHALLENGE_KEY_PREFIX = "webauthn:challenge:"


def _is_sign_count_regression(stored: int, new: int) -> bool:
    """Return True iff a non-zero ``new`` is not strictly greater than ``stored``.

    Authenticators that report ``sign_count == 0`` are exempt from the check
    (some platforms intentionally return 0). When both values are non-zero we
    expect strict monotonic growth — equality or regression indicates the
    credential may have been cloned.
    """
    return new > 0 and new <= stored


class WebAuthnService(LoggerMixin):
    """Coordinates WebAuthn ceremonies and credential lifecycle."""

    DOMAIN: ClassVar[str] = "auth"

    def __init__(
        self,
        *,
        staff_repository: StaffRepository,
        credential_repository: WebAuthnCredentialRepository,
        user_handle_repository: WebAuthnUserHandleRepository,
        auth_service: AuthService,
        redis_client: Redis,
        settings: WebAuthnSettings,
    ) -> None:
        super().__init__()
        self.staff_repository = staff_repository
        self.credential_repository = credential_repository
        self.user_handle_repository = user_handle_repository
        self.auth_service = auth_service
        self.redis_client = redis_client
        self.settings = settings

    # ------------------------------------------------------------------ helpers

    def _make_handle(self) -> str:
        """Opaque ceremony handle the client returns on /finish."""
        return secrets.token_urlsafe(32)

    def _challenge_key(self, handle: str) -> str:
        return f"{CHALLENGE_KEY_PREFIX}{handle}"

    async def _store_challenge(
        self,
        handle: str,
        payload: dict[str, Any],
    ) -> None:
        await self.redis_client.set(
            self._challenge_key(handle),
            json.dumps(payload),
            ex=self.settings.webauthn_challenge_ttl_seconds,
        )

    async def _pop_challenge(self, handle: str) -> dict[str, Any]:
        key = self._challenge_key(handle)
        raw = await self.redis_client.get(key)
        if raw is None:
            raise WebAuthnChallengeNotFoundError
        # Always delete first — single-use semantics, even on failure.
        await self.redis_client.delete(key)
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)  # type: ignore[no-any-return]

    # -------------------------------------------------------------- registration

    async def start_registration(
        self,
        staff: Staff,
    ) -> tuple[str, dict[str, Any]]:
        """Begin a registration ceremony for a logged-in staff member."""
        self.log_started("start_registration", staff_id=str(staff.id))

        user_handle = await self.user_handle_repository.get_or_create_for_staff(
            staff.id,
        )
        existing = await self.credential_repository.list_credential_ids_for_staff(
            staff.id,
        )
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=cred_id, transports=None)
            for cred_id, _transports in existing
        ]

        options = generate_registration_options(
            rp_id=self.settings.webauthn_rp_id,
            rp_name=self.settings.webauthn_rp_name,
            user_id=user_handle,
            user_name=staff.username or staff.email or str(staff.id),
            user_display_name=staff.name,
            attestation=AttestationConveyancePreference.NONE,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                resident_key=ResidentKeyRequirement.PREFERRED,
                user_verification=UserVerificationRequirement.REQUIRED,
            ),
            exclude_credentials=exclude_credentials,
        )

        handle = self._make_handle()
        await self._store_challenge(
            handle,
            {
                "challenge": bytes_to_base64url(options.challenge),
                "staff_id": str(staff.id),
                "kind": "registration",
            },
        )
        options_dict: dict[str, Any] = options_to_json_dict(options)
        self.log_completed(
            "start_registration",
            staff_id=str(staff.id),
            existing_credential_count=len(existing),
        )
        return handle, options_dict

    async def finish_registration(
        self,
        *,
        staff: Staff,
        handle: str,
        credential: dict[str, Any],
        device_name: str,
    ) -> WebAuthnCredential:
        """Verify the browser response and persist the new credential."""
        self.log_started("finish_registration", staff_id=str(staff.id))
        payload = await self._pop_challenge(handle)
        if payload.get("kind") != "registration" or payload.get("staff_id") != str(
            staff.id,
        ):
            self.log_rejected(
                "finish_registration",
                reason="challenge_mismatch",
                staff_id=str(staff.id),
            )
            raise WebAuthnChallengeNotFoundError

        try:
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(payload["challenge"]),
                expected_origin=self.settings.expected_origins_list,
                expected_rp_id=self.settings.webauthn_rp_id,
                require_user_verification=True,
            )
        except InvalidRegistrationResponse as exc:
            self.log_rejected(
                "finish_registration",
                reason="verification_failed",
                staff_id=str(staff.id),
                error=str(exc),
            )
            raise WebAuthnVerificationError from exc

        existing = await self.credential_repository.find_by_credential_id(
            verification.credential_id,
        )
        if existing is not None:
            self.log_rejected(
                "finish_registration",
                reason="duplicate_credential",
                staff_id=str(staff.id),
            )
            raise WebAuthnDuplicateCredentialError

        # Browser surfaces transports under credential.response.transports per W3C.
        transports = (
            credential.get("response", {}).get("transports") if credential else None
        )

        cred = await self.credential_repository.create(
            staff_id=staff.id,
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
            transports=transports,
            aaguid=verification.aaguid,
            credential_device_type=verification.credential_device_type.value,
            backup_eligible=verification.credential_backed_up,
            backup_state=verification.credential_backed_up,
            device_name=device_name,
        )
        self.log_completed(
            "finish_registration",
            staff_id=str(staff.id),
            credential_id=bytes_to_base64url(verification.credential_id),
            credential_device_type=verification.credential_device_type.value,
            aaguid=verification.aaguid,
        )
        return cred

    # ------------------------------------------------------------ authentication

    async def start_authentication(
        self,
        *,
        username: str | None,
    ) -> tuple[str, dict[str, Any]]:
        """Begin an authentication ceremony.

        When ``username`` is provided we restrict the ceremony to that user's
        credentials; otherwise the browser surfaces discoverable credentials.
        """
        self.log_started(
            "start_authentication",
            username_hint=username,
        )
        allow_credentials: list[PublicKeyCredentialDescriptor] = []
        staff_id_hint: str | None = None
        if username:
            staff = await self.staff_repository.find_by_username(username)
            if staff is not None:
                staff_id_hint = str(staff.id)
                rows = await self.credential_repository.list_credential_ids_for_staff(
                    staff.id,
                )
                allow_credentials = [
                    PublicKeyCredentialDescriptor(id=cred_id, transports=None)
                    for cred_id, _transports in rows
                ]

        options = generate_authentication_options(
            rp_id=self.settings.webauthn_rp_id,
            allow_credentials=allow_credentials or None,
            user_verification=UserVerificationRequirement.REQUIRED,
        )

        handle = self._make_handle()
        await self._store_challenge(
            handle,
            {
                "challenge": bytes_to_base64url(options.challenge),
                "staff_id": staff_id_hint,
                "kind": "authentication",
            },
        )
        options_dict: dict[str, Any] = options_to_json_dict(options)
        self.log_completed(
            "start_authentication",
            allow_credentials_count=len(allow_credentials),
        )
        return handle, options_dict

    async def finish_authentication(
        self,
        *,
        handle: str,
        credential: dict[str, Any],
    ) -> tuple[Staff, str, str, str]:
        """Verify a sign-in ceremony and mint the standard JWT cookie set."""
        self.log_started("finish_authentication")
        payload = await self._pop_challenge(handle)
        if payload.get("kind") != "authentication":
            raise WebAuthnChallengeNotFoundError

        # Resolve the credential row by the id the browser sent.
        raw_credential_id = credential.get("rawId") or credential.get("id")
        if not isinstance(raw_credential_id, str):
            raise WebAuthnVerificationError
        credential_id_bytes = base64url_to_bytes(raw_credential_id)

        stored = await self.credential_repository.find_by_credential_id(
            credential_id_bytes,
        )
        if stored is None:
            self.log_rejected(
                "finish_authentication",
                reason="revoked_or_unknown_credential",
            )
            raise WebAuthnVerificationError

        try:
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(payload["challenge"]),
                expected_rp_id=self.settings.webauthn_rp_id,
                expected_origin=self.settings.expected_origins_list,
                credential_public_key=stored.public_key,
                credential_current_sign_count=stored.sign_count,
                require_user_verification=True,
            )
        except InvalidAuthenticationResponse as exc:
            self.log_rejected(
                "finish_authentication",
                reason="verification_failed",
                error=str(exc),
            )
            raise WebAuthnVerificationError from exc

        if _is_sign_count_regression(stored.sign_count, verification.new_sign_count):
            await self.credential_repository.revoke_by_credential_id(
                credential_id_bytes,
            )
            self.log_rejected(
                "finish_authentication",
                reason="sign_count_regression",
                stored_count=stored.sign_count,
                received_count=verification.new_sign_count,
                staff_id=str(stored.staff_id),
                credential_id=bytes_to_base64url(credential_id_bytes),
            )
            raise WebAuthnVerificationError

        staff = await self.staff_repository.get_by_id(stored.staff_id)
        if staff is None:
            raise WebAuthnVerificationError

        # Mirror password-login state checks.
        if not staff.is_login_enabled or not staff.is_active:
            self.log_rejected(
                "finish_authentication",
                reason="login_disabled",
                staff_id=str(staff.id),
            )
            raise InvalidCredentialsError
        if self.auth_service._is_account_locked(staff):  # noqa: SLF001
            self.log_rejected(
                "finish_authentication",
                reason="account_locked",
                staff_id=str(staff.id),
            )
            raise AccountLockedError

        await self.credential_repository.update_sign_count(
            credential_id_bytes,
            verification.new_sign_count,
        )

        user_role = self.auth_service.get_user_role(staff)
        access_token = self.auth_service._create_access_token(  # noqa: SLF001
            staff.id,
            user_role,
        )
        refresh_token = self.auth_service._create_refresh_token(staff.id)  # noqa: SLF001
        csrf_token = secrets.token_urlsafe(32)

        self.log_completed(
            "finish_authentication",
            staff_id=str(staff.id),
            credential_id=bytes_to_base64url(credential_id_bytes),
            new_sign_count=verification.new_sign_count,
        )
        return staff, access_token, refresh_token, csrf_token

    # --------------------------------------------------------- list / revoke

    async def list_credentials(self, staff: Staff) -> list[WebAuthnCredential]:
        return await self.credential_repository.list_for_staff(staff.id)

    async def revoke_credential(
        self,
        *,
        credential_row_id: UUID,
        staff: Staff,
    ) -> None:
        from grins_platform.exceptions.auth import (  # noqa: PLC0415
            WebAuthnCredentialNotFoundError,
        )

        revoked = await self.credential_repository.revoke(
            credential_row_id,
            staff.id,
        )
        if not revoked:
            raise WebAuthnCredentialNotFoundError


__all__ = [
    "CHALLENGE_KEY_PREFIX",
    "WebAuthnService",
    "_is_sign_count_regression",
]
