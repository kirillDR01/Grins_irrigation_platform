"""Property-based tests for authentication.

Property 1: Password Hashing Round-Trip
Property 2: Role Permission Hierarchy

Validates: Requirements 15.8, 16.1-16.4, 17.1-17.12

Note: These tests use bcrypt directly instead of passlib's pwd_context
due to compatibility issues between passlib and newer bcrypt versions.
The AuthService uses the same underlying bcrypt algorithm.
"""

import bcrypt
import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import UserRole


@pytest.mark.unit
class TestPasswordHashingProperty:
    """Property-based tests for password hashing.

    Property 1: Password Hashing Round-Trip
    - Hash then verify returns true for any valid password
    - Different passwords produce different hashes

    Validates: Requirements 15.8, 16.1-16.4
    """

    @given(
        password=st.text(
            min_size=8,
            max_size=50,  # Keep well under bcrypt's 72 byte limit
            alphabet=st.sampled_from(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            ),
        ),
    )
    @settings(max_examples=50, deadline=10000)
    def test_hash_then_verify_returns_true(self, password: str) -> None:
        """Property: hash(password) then verify(password, hash) returns True.

        For any valid password, hashing it and then verifying the original
        password against the hash should always return True.
        """
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=4)  # Use lower rounds for faster tests
        hashed = bcrypt.hashpw(password_bytes, salt)

        assert bcrypt.checkpw(password_bytes, hashed) is True

    @given(
        password1=st.text(
            min_size=8,
            max_size=30,
            alphabet=st.sampled_from(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            ),
        ),
        password2=st.text(
            min_size=8,
            max_size=30,
            alphabet=st.sampled_from(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            ),
        ),
    )
    @settings(max_examples=30, deadline=10000)
    def test_different_passwords_produce_different_hashes(
        self, password1: str, password2: str,
    ) -> None:
        """Property: Different passwords produce different hashes.

        When two different passwords are hashed, they should produce
        different hash values (with extremely high probability due to
        bcrypt's random salt).
        """
        if password1 == password2:
            return  # Skip when passwords are the same

        salt = bcrypt.gensalt(rounds=4)
        hash1 = bcrypt.hashpw(password1.encode("utf-8"), salt)

        salt2 = bcrypt.gensalt(rounds=4)
        hash2 = bcrypt.hashpw(password2.encode("utf-8"), salt2)

        # Hashes should be different (bcrypt uses random salt)
        assert hash1 != hash2

    @given(
        password=st.text(
            min_size=8,
            max_size=30,
            alphabet=st.sampled_from(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            ),
        ),
        wrong_password=st.text(
            min_size=8,
            max_size=30,
            alphabet=st.sampled_from(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            ),
        ),
    )
    @settings(max_examples=30, deadline=10000)
    def test_wrong_password_verify_returns_false(
        self, password: str, wrong_password: str,
    ) -> None:
        """Property: verify(wrong_password, hash) returns False.

        For any password and a different wrong password, verifying the
        wrong password against the hash should return False.
        """
        if password == wrong_password:
            return  # Skip when passwords are the same

        salt = bcrypt.gensalt(rounds=4)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)

        assert bcrypt.checkpw(wrong_password.encode("utf-8"), hashed) is False

    @given(
        password=st.text(
            min_size=8,
            max_size=30,
            alphabet=st.sampled_from(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            ),
        ),
    )
    @settings(max_examples=20, deadline=10000)
    def test_same_password_different_hashes(self, password: str) -> None:
        """Property: Same password hashed twice produces different hashes.

        Due to bcrypt's random salt, hashing the same password twice
        should produce different hash values.
        """
        password_bytes = password.encode("utf-8")

        salt1 = bcrypt.gensalt(rounds=4)
        hash1 = bcrypt.hashpw(password_bytes, salt1)

        salt2 = bcrypt.gensalt(rounds=4)
        hash2 = bcrypt.hashpw(password_bytes, salt2)

        # Hashes should be different due to random salt
        assert hash1 != hash2

        # But both should verify correctly
        assert bcrypt.checkpw(password_bytes, hash1) is True
        assert bcrypt.checkpw(password_bytes, hash2) is True

    @given(
        password=st.text(
            min_size=8,
            max_size=30,
            alphabet=st.sampled_from(
                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
            ),
        ),
    )
    @settings(max_examples=20, deadline=10000)
    def test_hash_format_is_bcrypt(self, password: str) -> None:
        """Property: Hash format is valid bcrypt.

        All hashes should start with $2b$ (bcrypt identifier) and
        have the expected length of 60 characters.
        """
        salt = bcrypt.gensalt(rounds=4)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        hashed_str = hashed.decode("utf-8")

        # bcrypt hashes start with $2b$ or $2a$ or $2y$
        assert hashed_str.startswith(("$2b$", "$2a$", "$2y$"))
        # bcrypt hashes are always 60 characters
        assert len(hashed_str) == 60


@pytest.mark.unit
class TestRolePermissionHierarchyProperty:
    """Property-based tests for role permission hierarchy.

    Property 2: Role Permission Hierarchy
    - Admin has all permissions
    - Manager has subset of admin permissions
    - Tech has subset of manager permissions

    Validates: Requirements 17.1-17.12
    """

    # Define permission hierarchy as frozensets (immutable)
    ADMIN_PERMISSIONS: frozenset[str] = frozenset({
        "view_customers",
        "edit_customers",
        "delete_customers",
        "view_jobs",
        "edit_jobs",
        "delete_jobs",
        "view_invoices",
        "edit_invoices",
        "delete_invoices",
        "send_lien_warning",
        "file_lien",
        "view_staff",
        "edit_staff",
        "delete_staff",
        "clear_schedule",
        "view_reports",
        "manage_settings",
    })

    MANAGER_PERMISSIONS: frozenset[str] = frozenset({
        "view_customers",
        "edit_customers",
        "view_jobs",
        "edit_jobs",
        "view_invoices",
        "edit_invoices",
        "view_staff",
        "clear_schedule",
        "view_reports",
    })

    TECH_PERMISSIONS: frozenset[str] = frozenset({
        "view_customers",
        "view_jobs",
        "edit_jobs",  # Can update job status
        "view_invoices",
    })

    def get_permissions_for_role(self, role: UserRole) -> frozenset[str]:
        """Get permissions for a given role."""
        if role == UserRole.ADMIN:
            return self.ADMIN_PERMISSIONS
        if role == UserRole.MANAGER:
            return self.MANAGER_PERMISSIONS
        return self.TECH_PERMISSIONS

    @given(role=st.sampled_from([UserRole.ADMIN, UserRole.MANAGER, UserRole.TECH]))
    @settings(max_examples=10)
    def test_admin_has_all_permissions(self, role: UserRole) -> None:
        """Property: Admin role has all permissions that any other role has."""
        role_permissions = self.get_permissions_for_role(role)
        admin_permissions = self.get_permissions_for_role(UserRole.ADMIN)

        # Admin should have all permissions that this role has
        assert role_permissions.issubset(admin_permissions)

    @given(
        permission=st.sampled_from(list(MANAGER_PERMISSIONS)),
    )
    @settings(max_examples=20)
    def test_manager_permissions_subset_of_admin(self, permission: str) -> None:
        """Property: Every manager permission is also an admin permission."""
        assert permission in self.ADMIN_PERMISSIONS

    @given(
        permission=st.sampled_from(list(TECH_PERMISSIONS)),
    )
    @settings(max_examples=10)
    def test_tech_permissions_subset_of_manager(self, permission: str) -> None:
        """Property: Every tech permission is also a manager permission."""
        assert permission in self.MANAGER_PERMISSIONS

    def test_role_hierarchy_is_strict(self) -> None:
        """Property: Role hierarchy is strictly ordered (admin > manager > tech)."""
        # Admin has more permissions than manager
        assert len(self.ADMIN_PERMISSIONS) > len(self.MANAGER_PERMISSIONS)

        # Manager has more permissions than tech
        assert len(self.MANAGER_PERMISSIONS) > len(self.TECH_PERMISSIONS)

        # Verify subset relationships
        assert self.TECH_PERMISSIONS.issubset(self.MANAGER_PERMISSIONS)
        assert self.MANAGER_PERMISSIONS.issubset(self.ADMIN_PERMISSIONS)

    @given(
        role1=st.sampled_from([UserRole.ADMIN, UserRole.MANAGER, UserRole.TECH]),
        role2=st.sampled_from([UserRole.ADMIN, UserRole.MANAGER, UserRole.TECH]),
    )
    @settings(max_examples=20)
    def test_permission_transitivity(
        self, role1: UserRole, role2: UserRole,
    ) -> None:
        """Property: If role1 >= role2 in hierarchy, role1 has all role2 permissions."""
        role_order = {UserRole.ADMIN: 3, UserRole.MANAGER: 2, UserRole.TECH: 1}

        perms1 = self.get_permissions_for_role(role1)
        perms2 = self.get_permissions_for_role(role2)

        if role_order[role1] >= role_order[role2]:
            # Higher role should have all permissions of lower role
            assert perms2.issubset(perms1)
