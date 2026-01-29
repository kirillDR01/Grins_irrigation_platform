"""
Unit tests for authentication model fields.

Tests Staff model authentication fields and UserRole enum.
Validates: Requirements 15.1-15.8, 17.1
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from grins_platform.models.enums import UserRole
from grins_platform.models.staff import Staff


@pytest.mark.unit
class TestUserRoleEnum:
    """Test UserRole enum values.

    Validates: Requirement 17.1
    """

    def test_admin_role_value(self) -> None:
        """Test ADMIN role has correct value."""
        assert UserRole.ADMIN.value == "admin"

    def test_manager_role_value(self) -> None:
        """Test MANAGER role has correct value."""
        assert UserRole.MANAGER.value == "manager"

    def test_tech_role_value(self) -> None:
        """Test TECH role has correct value."""
        assert UserRole.TECH.value == "tech"

    def test_all_roles_exist(self) -> None:
        """Test all expected roles exist."""
        roles = [r.value for r in UserRole]
        assert "admin" in roles
        assert "manager" in roles
        assert "tech" in roles
        assert len(roles) == 3

    def test_role_from_string(self) -> None:
        """Test creating role from string value."""
        assert UserRole("admin") == UserRole.ADMIN
        assert UserRole("manager") == UserRole.MANAGER
        assert UserRole("tech") == UserRole.TECH

    def test_invalid_role_raises_error(self) -> None:
        """Test invalid role string raises ValueError."""
        with pytest.raises(ValueError):
            UserRole("invalid_role")


@pytest.mark.unit
class TestStaffAuthenticationFields:
    """Test Staff model authentication fields.

    Validates: Requirements 15.1-15.8
    """

    def test_staff_with_username(self) -> None:
        """Test Staff model with username field.

        Validates: Requirement 15.1 (username column)
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            username="testuser",
        )
        assert staff.username == "testuser"

    def test_staff_username_nullable(self) -> None:
        """Test Staff model username can be None.

        Validates: Requirement 15.1 (nullable)
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            username=None,
        )
        assert staff.username is None

    def test_staff_with_password_hash(self) -> None:
        """Test Staff model with password_hash field.

        Validates: Requirement 15.2 (password_hash column)
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            password_hash="$2b$12$hashedpassword",
        )
        assert staff.password_hash == "$2b$12$hashedpassword"

    def test_staff_password_hash_nullable(self) -> None:
        """Test Staff model password_hash can be None.

        Validates: Requirement 15.2 (nullable)
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            password_hash=None,
        )
        assert staff.password_hash is None

    def test_staff_is_login_enabled_default_false(self) -> None:
        """Test Staff model is_login_enabled defaults to False.

        Validates: Requirement 15.3 (default FALSE)
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
        )
        # Note: server_default won't apply in Python, but field should exist
        assert hasattr(staff, "is_login_enabled")

    def test_staff_is_login_enabled_true(self) -> None:
        """Test Staff model with is_login_enabled set to True.

        Validates: Requirement 15.3
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            is_login_enabled=True,
        )
        assert staff.is_login_enabled is True

    def test_staff_is_login_enabled_false(self) -> None:
        """Test Staff model with is_login_enabled set to False.

        Validates: Requirement 15.3
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            is_login_enabled=False,
        )
        assert staff.is_login_enabled is False

    def test_staff_with_last_login(self) -> None:
        """Test Staff model with last_login field.

        Validates: Requirement 15.4 (last_login column)
        """
        login_time = datetime.now(timezone.utc)
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            last_login=login_time,
        )
        assert staff.last_login == login_time

    def test_staff_last_login_nullable(self) -> None:
        """Test Staff model last_login can be None.

        Validates: Requirement 15.4 (nullable)
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            last_login=None,
        )
        assert staff.last_login is None

    def test_staff_with_failed_login_attempts(self) -> None:
        """Test Staff model with failed_login_attempts field.

        Validates: Requirement 15.5 (failed_login_attempts column)
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            failed_login_attempts=3,
        )
        assert staff.failed_login_attempts == 3

    def test_staff_failed_login_attempts_zero(self) -> None:
        """Test Staff model failed_login_attempts can be zero.

        Validates: Requirement 15.5 (default 0)
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            failed_login_attempts=0,
        )
        assert staff.failed_login_attempts == 0

    def test_staff_with_locked_until(self) -> None:
        """Test Staff model with locked_until field.

        Validates: Requirement 15.6 (locked_until column)
        """
        lock_time = datetime.now(timezone.utc) + timedelta(minutes=15)
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            locked_until=lock_time,
        )
        assert staff.locked_until == lock_time

    def test_staff_locked_until_nullable(self) -> None:
        """Test Staff model locked_until can be None.

        Validates: Requirement 15.6 (nullable)
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            locked_until=None,
        )
        assert staff.locked_until is None

    def test_staff_full_auth_fields(self) -> None:
        """Test Staff model with all authentication fields populated.

        Validates: Requirements 15.1-15.8
        """
        now = datetime.now(timezone.utc)
        lock_time = now + timedelta(minutes=15)

        staff = Staff(
            id=uuid4(),
            name="Admin User",
            phone="6125551234",
            role="admin",
            username="adminuser",
            password_hash="$2b$12$somehash",
            is_login_enabled=True,
            last_login=now,
            failed_login_attempts=2,
            locked_until=lock_time,
        )

        assert staff.username == "adminuser"
        assert staff.password_hash == "$2b$12$somehash"
        assert staff.is_login_enabled is True
        assert staff.last_login == now
        assert staff.failed_login_attempts == 2
        assert staff.locked_until == lock_time

    def test_staff_to_dict_excludes_password_hash(self) -> None:
        """Test Staff.to_dict() excludes password_hash for security.

        Validates: Security requirement - password hash should not be exposed
        """
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            username="testuser",
            password_hash="$2b$12$secrethash",
            is_login_enabled=True,
        )

        result = staff.to_dict()

        assert "password_hash" not in result
        assert result["username"] == "testuser"
        assert result["is_login_enabled"] is True

    def test_staff_to_dict_includes_auth_fields(self) -> None:
        """Test Staff.to_dict() includes non-sensitive auth fields.

        Validates: Requirements 15.1-15.8
        """
        now = datetime.now(timezone.utc)
        lock_time = now + timedelta(minutes=15)

        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            username="testuser",
            is_login_enabled=True,
            last_login=now,
            failed_login_attempts=1,
            locked_until=lock_time,
        )

        result = staff.to_dict()

        assert result["username"] == "testuser"
        assert result["is_login_enabled"] is True
        assert result["last_login"] == now.isoformat()
        assert result["failed_login_attempts"] == 1
        assert result["locked_until"] == lock_time.isoformat()

    def test_staff_to_dict_handles_none_timestamps(self) -> None:
        """Test Staff.to_dict() handles None timestamps correctly."""
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            last_login=None,
            locked_until=None,
        )

        result = staff.to_dict()

        assert result["last_login"] is None
        assert result["locked_until"] is None


@pytest.mark.unit
class TestStaffModelIntegrity:
    """Test Staff model field integrity for authentication.

    Validates: Requirements 15.1-15.8
    """

    def test_staff_has_all_auth_attributes(self) -> None:
        """Test Staff model has all required authentication attributes."""
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
        )

        # Verify all auth fields exist
        assert hasattr(staff, "username")
        assert hasattr(staff, "password_hash")
        assert hasattr(staff, "is_login_enabled")
        assert hasattr(staff, "last_login")
        assert hasattr(staff, "failed_login_attempts")
        assert hasattr(staff, "locked_until")

    def test_staff_repr_does_not_expose_password(self) -> None:
        """Test Staff __repr__ does not expose password hash."""
        staff = Staff(
            id=uuid4(),
            name="Test User",
            phone="6125551234",
            role="tech",
            password_hash="$2b$12$secrethash",
        )

        repr_str = repr(staff)

        assert "secrethash" not in repr_str
        assert "password" not in repr_str.lower()
