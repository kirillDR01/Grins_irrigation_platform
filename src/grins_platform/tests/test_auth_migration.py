"""Tests for authentication migration.

This module tests the staff authentication columns migration:
- Verifies columns are added correctly
- Tests rollback functionality
- Validates constraints and indexes

Requirements: 15.1-15.8
"""

import importlib.util
from collections.abc import Generator
from pathlib import Path
from types import ModuleType

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from grins_platform.database import DatabaseSettings


@pytest.fixture
def sync_engine() -> Engine:
    """Create a sync engine for migration testing."""
    settings = DatabaseSettings()
    sync_url = settings.database_url
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return create_engine(sync_url, pool_pre_ping=True)


@pytest.fixture
def sync_session(sync_engine: Engine) -> Generator[Session, None, None]:
    """Create a sync session for testing."""
    session_factory = sessionmaker(bind=sync_engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _load_migration_module() -> ModuleType:
    """Load the authentication migration module dynamically."""
    migration_path = (
        Path(__file__).parent.parent
        / "migrations"
        / "versions"
        / "20250621_100000_add_staff_authentication_columns.py"
    )
    spec = importlib.util.spec_from_file_location("migration", str(migration_path))
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


class TestAuthenticationMigration:
    """Test suite for authentication migration (20250621_100000)."""

    def test_staff_table_has_username_column(self, sync_engine: Engine) -> None:
        """Test that staff table has username column after migration."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("staff")}

        assert "username" in columns, "username column should exist"
        assert columns["username"]["nullable"] is True
        # VARCHAR(50)
        assert str(columns["username"]["type"]).startswith("VARCHAR")

    def test_staff_table_has_password_hash_column(self, sync_engine: Engine) -> None:
        """Test that staff table has password_hash column after migration."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("staff")}

        assert "password_hash" in columns, "password_hash column should exist"
        assert columns["password_hash"]["nullable"] is True
        # VARCHAR(255)
        assert str(columns["password_hash"]["type"]).startswith("VARCHAR")

    def test_staff_table_has_is_login_enabled_column(
        self, sync_engine: Engine,
    ) -> None:
        """Test that staff table has is_login_enabled column after migration."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("staff")}

        assert "is_login_enabled" in columns, "is_login_enabled column should exist"
        assert columns["is_login_enabled"]["nullable"] is False
        assert str(columns["is_login_enabled"]["type"]).upper() == "BOOLEAN"

    def test_staff_table_has_last_login_column(self, sync_engine: Engine) -> None:
        """Test that staff table has last_login column after migration."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("staff")}

        assert "last_login" in columns, "last_login column should exist"
        assert columns["last_login"]["nullable"] is True
        # TIMESTAMP WITH TIME ZONE
        assert "TIMESTAMP" in str(columns["last_login"]["type"]).upper()

    def test_staff_table_has_failed_login_attempts_column(
        self, sync_engine: Engine,
    ) -> None:
        """Test that staff table has failed_login_attempts column after migration."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("staff")}

        assert (
            "failed_login_attempts" in columns
        ), "failed_login_attempts column should exist"
        assert columns["failed_login_attempts"]["nullable"] is False
        assert str(columns["failed_login_attempts"]["type"]).upper() == "INTEGER"

    def test_staff_table_has_locked_until_column(self, sync_engine: Engine) -> None:
        """Test that staff table has locked_until column after migration."""
        inspector = inspect(sync_engine)
        columns = {col["name"]: col for col in inspector.get_columns("staff")}

        assert "locked_until" in columns, "locked_until column should exist"
        assert columns["locked_until"]["nullable"] is True
        # TIMESTAMP WITH TIME ZONE
        assert "TIMESTAMP" in str(columns["locked_until"]["type"]).upper()

    def test_username_index_exists(self, sync_engine: Engine) -> None:
        """Test that unique index on username exists."""
        inspector = inspect(sync_engine)
        indexes = inspector.get_indexes("staff")

        username_index = None
        for idx in indexes:
            if "username" in idx.get("column_names", []):
                username_index = idx
                break

        assert username_index is not None, "Index on username should exist"
        assert username_index["unique"] is True, "Username index should be unique"

    def test_is_login_enabled_default_value(
        self, sync_session: Session,
    ) -> None:
        """Test that is_login_enabled defaults to FALSE."""
        # Query the column default from information_schema
        result = sync_session.execute(
            text("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = 'staff'
                AND column_name = 'is_login_enabled'
            """),
        )
        row = result.fetchone()
        assert row is not None
        # Default should be false
        assert row[0] is not None
        assert "false" in str(row[0]).lower()

    def test_failed_login_attempts_default_value(
        self, sync_session: Session,
    ) -> None:
        """Test that failed_login_attempts defaults to 0."""
        result = sync_session.execute(
            text("""
                SELECT column_default
                FROM information_schema.columns
                WHERE table_name = 'staff'
                AND column_name = 'failed_login_attempts'
            """),
        )
        row = result.fetchone()
        assert row is not None
        # Default should be 0
        assert row[0] is not None
        assert "0" in str(row[0])

    def test_all_auth_columns_present(self, sync_engine: Engine) -> None:
        """Test that all authentication columns are present."""
        inspector = inspect(sync_engine)
        columns = {col["name"] for col in inspector.get_columns("staff")}

        expected_auth_columns = {
            "username",
            "password_hash",
            "is_login_enabled",
            "last_login",
            "failed_login_attempts",
            "locked_until",
        }

        missing = expected_auth_columns - columns
        assert not missing, f"Missing authentication columns: {missing}"


class TestMigrationRollback:
    """Test suite for migration rollback functionality.

    Note: These tests verify the migration structure supports rollback.
    Actual rollback testing requires running alembic commands.
    """

    def test_migration_has_downgrade_function(self) -> None:
        """Test that migration file has downgrade function."""
        migration = _load_migration_module()

        # Verify downgrade function exists
        assert hasattr(migration, "downgrade")
        assert callable(migration.downgrade)

    def test_migration_has_upgrade_function(self) -> None:
        """Test that migration file has upgrade function."""
        migration = _load_migration_module()

        # Verify upgrade function exists
        assert hasattr(migration, "upgrade")
        assert callable(migration.upgrade)

    def test_migration_revision_chain(self) -> None:
        """Test that migration has correct revision chain."""
        migration = _load_migration_module()

        assert migration.revision == "20250621_100000"
        assert migration.down_revision == "20250620_100200"
