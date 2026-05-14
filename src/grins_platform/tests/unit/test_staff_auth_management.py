"""Unit tests for Cluster F — admin staff auth management.

Covers:
- Admin password-strength validator (positive + negative + blocklist).
- ResetPasswordRequest schema.
- StaffService.create_staff routing username/password/is_login_enabled.
- StaffService.update_staff routing password rotation.
- StaffService.reset_password clearing lockout state.
- Username uniqueness collision returning HTTP 409.

Validates: Cluster F — Admin Staff Auth UI.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from grins_platform.exceptions import StaffNotFoundError
from grins_platform.models.enums import StaffRole
from grins_platform.schemas.staff import (
    ResetPasswordRequest,
    StaffCreate,
    StaffUpdate,
    _validate_admin_password,
)
from grins_platform.services.staff_service import StaffService

# =============================================================================
# Validator — _validate_admin_password
# =============================================================================


@pytest.mark.unit
class TestValidateAdminPassword:
    """Tests for the admin password-strength validator."""

    def test_accepts_mixed_letter_and_digit(self) -> None:
        """A valid password with letters and digits is accepted."""
        assert _validate_admin_password("Abcd1234", username=None) == "Abcd1234"

    def test_accepts_lowercase_only_with_digit(self) -> None:
        """Lowercase-only passwords are accepted (no case requirement)."""
        assert _validate_admin_password("goodpass1", username=None) == "goodpass1"

    def test_rejects_short_password(self) -> None:
        """Passwords shorter than 8 chars are rejected."""
        with pytest.raises(ValueError, match="at least 8"):
            _validate_admin_password("short1", username=None)

    def test_rejects_password_with_no_letter(self) -> None:
        """Passwords with no letter are rejected."""
        with pytest.raises(ValueError, match="letter"):
            _validate_admin_password("12345678", username=None)

    def test_rejects_password_with_no_digit(self) -> None:
        """Passwords with no digit are rejected."""
        with pytest.raises(ValueError, match="number"):
            _validate_admin_password("nodigits", username=None)

    def test_rejects_blocklisted_password(self) -> None:
        """Common passwords on the blocklist are rejected."""
        with pytest.raises(ValueError, match="common"):
            _validate_admin_password("admin123", username=None)

    def test_blocklist_is_case_insensitive(self) -> None:
        """Blocklist match is case-insensitive."""
        with pytest.raises(ValueError, match="common"):
            _validate_admin_password("Admin123", username=None)

    def test_rejects_password_matching_username(self) -> None:
        """Password equal to username is rejected."""
        with pytest.raises(ValueError, match="username"):
            _validate_admin_password("Bob12345", username="Bob12345")


# =============================================================================
# ResetPasswordRequest schema
# =============================================================================


@pytest.mark.unit
class TestResetPasswordRequest:
    """Tests for the ResetPasswordRequest schema."""

    def test_accepts_valid_password(self) -> None:
        """Valid new password is accepted."""
        req = ResetPasswordRequest(new_password="Goodpass1")
        assert req.new_password == "Goodpass1"

    def test_rejects_short_password(self) -> None:
        """Short passwords are rejected at the schema layer."""
        with pytest.raises(ValidationError):
            ResetPasswordRequest(new_password="short")

    def test_rejects_blocklisted_password(self) -> None:
        """Blocklist enforced via schema validator."""
        with pytest.raises(ValidationError):
            ResetPasswordRequest(new_password="password")


# =============================================================================
# StaffCreate / StaffUpdate password validation
# =============================================================================


@pytest.mark.unit
class TestStaffCreatePasswordValidation:
    """Tests for password validation embedded in StaffCreate."""

    def test_accepts_creation_without_password(self) -> None:
        """No password supplied → schema passes."""
        data = StaffCreate(
            name="Alice",
            phone="6125551234",
            role=StaffRole.TECH,
        )
        assert data.password is None
        assert data.username is None
        assert data.is_login_enabled is None

    def test_accepts_creation_with_credentials(self) -> None:
        """Username + valid password + is_login_enabled flow through."""
        data = StaffCreate(
            name="Alice",
            phone="6125551234",
            role=StaffRole.TECH,
            username="alice",
            password="Goodpass1",
            is_login_enabled=True,
        )
        assert data.username == "alice"
        assert data.password == "Goodpass1"
        assert data.is_login_enabled is True

    def test_rejects_password_matching_username(self) -> None:
        """Password equal to username is rejected at the schema layer."""
        with pytest.raises(ValidationError):
            StaffCreate(
                name="Bob",
                phone="6125551234",
                role=StaffRole.TECH,
                username="Bob12345",
                password="Bob12345",
            )

    def test_rejects_invalid_username_pattern(self) -> None:
        """Usernames with disallowed characters are rejected."""
        with pytest.raises(ValidationError):
            StaffCreate(
                name="Bob",
                phone="6125551234",
                role=StaffRole.TECH,
                username="has spaces",
            )


@pytest.mark.unit
class TestStaffUpdatePasswordValidation:
    """Tests for password validation embedded in StaffUpdate."""

    def test_accepts_update_with_password_and_username(self) -> None:
        """A password+username update validates."""
        data = StaffUpdate(password="Goodpass1", username="alice")
        assert data.password == "Goodpass1"

    def test_rejects_weak_password_in_update(self) -> None:
        """Weak passwords are rejected in updates too."""
        with pytest.raises(ValidationError):
            StaffUpdate(password="weak")


# =============================================================================
# StaffService — create_staff
# =============================================================================


@pytest.mark.unit
class TestStaffServiceCreateWithCredentials:
    """Tests for StaffService.create_staff with auth fields."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Mock StaffRepository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository: AsyncMock) -> StaffService:
        """Service with mock repo."""
        return StaffService(mock_repository)

    @pytest.mark.asyncio
    async def test_create_passes_username_and_hash_to_repo(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """create_staff hashes password and passes auth kwargs to the repo."""
        mock_staff = MagicMock()
        mock_staff.id = uuid4()
        mock_repository.create.return_value = mock_staff
        mock_repository.find_by_username.return_value = None

        data = StaffCreate(
            name="Alice",
            phone="6125551234",
            role=StaffRole.TECH,
            username="alice",
            password="Goodpass1",
            is_login_enabled=True,
        )

        await service.create_staff(data)

        kwargs = mock_repository.create.call_args.kwargs
        assert kwargs["username"] == "alice"
        assert kwargs["is_login_enabled"] is True
        assert kwargs["password_hash"] is not None
        assert kwargs["password_hash"].startswith("$2b$12$")
        assert kwargs["password_hash"] != "Goodpass1"

    @pytest.mark.asyncio
    async def test_create_without_password_passes_none_hash(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """No password → repo receives password_hash=None."""
        mock_staff = MagicMock()
        mock_staff.id = uuid4()
        mock_repository.create.return_value = mock_staff
        mock_repository.find_by_username.return_value = None

        data = StaffCreate(
            name="Alice",
            phone="6125551234",
            role=StaffRole.TECH,
        )

        await service.create_staff(data)

        kwargs = mock_repository.create.call_args.kwargs
        assert kwargs["password_hash"] is None
        assert kwargs["is_login_enabled"] is False
        assert kwargs["username"] is None

    @pytest.mark.asyncio
    async def test_create_rejects_username_collision(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Pre-existing username → HTTPException 409."""
        existing = MagicMock()
        existing.id = uuid4()
        mock_repository.find_by_username.return_value = existing

        data = StaffCreate(
            name="Alice",
            phone="6125551234",
            role=StaffRole.TECH,
            username="taken",
        )

        with pytest.raises(HTTPException) as exc:
            await service.create_staff(data)
        assert exc.value.status_code == 409
        mock_repository.create.assert_not_called()


# =============================================================================
# StaffService — update_staff
# =============================================================================


@pytest.mark.unit
class TestStaffServiceUpdateWithCredentials:
    """Tests for StaffService.update_staff routing auth fields."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Mock StaffRepository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository: AsyncMock) -> StaffService:
        """Service with mock repo."""
        return StaffService(mock_repository)

    @pytest.mark.asyncio
    async def test_update_password_hashes_and_calls_update_auth_fields(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """A password update routes through update_auth_fields, not repo.update."""
        staff_id = uuid4()
        existing = MagicMock()
        existing.id = staff_id
        existing.username = None
        existing.password_hash = None
        mock_repository.get_by_id.return_value = existing
        mock_repository.update.return_value = existing
        mock_repository.update_auth_fields.return_value = existing

        data = StaffUpdate(password="Goodpass1")
        await service.update_staff(staff_id, data)

        mock_repository.update_auth_fields.assert_called_once()
        kwargs = mock_repository.update_auth_fields.call_args.kwargs
        assert kwargs["password_hash"].startswith("$2b$12$")

        # password must NOT be passed to the generic repo.update path
        # (Staff has no `password` column — only password_hash).
        update_call = mock_repository.update.call_args
        update_data = (
            update_call.args[1]
            if len(update_call.args) > 1
            else (update_call.kwargs.get("data", {}))
        )
        assert "password" not in update_data

    @pytest.mark.asyncio
    async def test_update_rejects_username_collision_with_other_staff(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """A username already taken by another staff → 409."""
        staff_id = uuid4()
        existing = MagicMock()
        existing.id = staff_id
        existing.username = None
        existing.password_hash = None
        mock_repository.get_by_id.return_value = existing

        collision = MagicMock()
        collision.id = uuid4()  # different staff
        mock_repository.find_by_username.return_value = collision

        data = StaffUpdate(username="taken")
        with pytest.raises(HTTPException) as exc:
            await service.update_staff(staff_id, data)
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_username_to_own_existing_username_is_noop(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Re-sending the same username does not trigger a uniqueness check."""
        staff_id = uuid4()
        existing = MagicMock()
        existing.id = staff_id
        existing.username = "alice"
        existing.password_hash = None
        mock_repository.get_by_id.return_value = existing
        mock_repository.update.return_value = existing

        data = StaffUpdate(username="alice")
        await service.update_staff(staff_id, data)

        mock_repository.find_by_username.assert_not_called()


# =============================================================================
# StaffService — reset_password
# =============================================================================


@pytest.mark.unit
class TestStaffServiceResetPassword:
    """Tests for StaffService.reset_password."""

    @pytest.fixture
    def mock_repository(self) -> AsyncMock:
        """Mock StaffRepository."""
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_repository: AsyncMock) -> StaffService:
        """Service with mock repo."""
        return StaffService(mock_repository)

    @pytest.mark.asyncio
    async def test_reset_password_clears_lockout(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Reset clears failed_login_attempts and locked_until."""
        staff_id = uuid4()
        existing = MagicMock()
        existing.id = staff_id
        mock_repository.get_by_id.return_value = existing
        mock_repository.update_auth_fields.return_value = existing

        await service.reset_password(staff_id, "Newpass1")

        kwargs = mock_repository.update_auth_fields.call_args.kwargs
        assert kwargs["password_hash"].startswith("$2b$12$")
        assert kwargs["failed_login_attempts"] == 0
        assert kwargs["locked_until"] is None

    @pytest.mark.asyncio
    async def test_reset_password_not_found_raises(
        self,
        service: StaffService,
        mock_repository: AsyncMock,
    ) -> None:
        """Missing staff → StaffNotFoundError."""
        staff_id = uuid4()
        mock_repository.get_by_id.return_value = None

        with pytest.raises(StaffNotFoundError):
            await service.reset_password(staff_id, "Newpass1")

        mock_repository.update_auth_fields.assert_not_called()
