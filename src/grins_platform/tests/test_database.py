"""Tests for database configuration and connection management."""

from grins_platform.database import (
    Base,
    DatabaseManager,
    DatabaseSettings,
    get_database_manager,
)


class TestDatabaseSettings:
    """Test suite for DatabaseSettings."""

    def test_default_settings(self) -> None:
        """Test default database settings are loaded."""
        settings = DatabaseSettings()
        assert settings.pool_size == 5
        assert settings.max_overflow == 10
        assert settings.pool_timeout == 30
        assert settings.pool_recycle == 1800

    def test_async_database_url_postgresql(self) -> None:
        """Test async URL conversion for postgresql:// prefix."""
        settings = DatabaseSettings(
            database_url="postgresql://user:pass@localhost:5432/db",
        )
        assert (
            settings.async_database_url
            == "postgresql+asyncpg://user:pass@localhost:5432/db"
        )

    def test_async_database_url_postgres(self) -> None:
        """Test async URL conversion for postgres:// prefix."""
        settings = DatabaseSettings(
            database_url="postgres://user:pass@localhost:5432/db",
        )
        assert (
            settings.async_database_url
            == "postgresql+asyncpg://user:pass@localhost:5432/db"
        )

    def test_async_database_url_already_async(self) -> None:
        """Test async URL is unchanged if already in async format."""
        settings = DatabaseSettings(
            database_url="postgresql+asyncpg://user:pass@localhost:5432/db",
        )
        assert (
            settings.async_database_url
            == "postgresql+asyncpg://user:pass@localhost:5432/db"
        )


class TestDatabaseManager:
    """Test suite for DatabaseManager."""

    def test_init_with_default_settings(self) -> None:
        """Test DatabaseManager initializes with default settings."""
        manager = DatabaseManager()
        assert manager.settings is not None
        assert manager._engine is None
        assert manager._session_factory is None

    def test_init_with_custom_settings(self) -> None:
        """Test DatabaseManager initializes with custom settings."""
        settings = DatabaseSettings(
            database_url="postgresql://custom:custom@localhost:5432/custom",
            pool_size=10,
        )
        manager = DatabaseManager(settings=settings)
        assert manager.settings.pool_size == 10
        assert "custom" in manager.settings.database_url

    def test_engine_property_creates_engine(self) -> None:
        """Test engine property creates engine on first access."""
        settings = DatabaseSettings(
            database_url="postgresql://user:pass@localhost:5432/db",
        )
        manager = DatabaseManager(settings=settings)

        # Engine should be created on first access
        engine = manager.engine
        assert engine is not None
        assert manager._engine is engine

        # Second access should return same engine
        assert manager.engine is engine

    def test_session_factory_property_creates_factory(self) -> None:
        """Test session_factory property creates factory on first access."""
        settings = DatabaseSettings(
            database_url="postgresql://user:pass@localhost:5432/db",
        )
        manager = DatabaseManager(settings=settings)

        # Factory should be created on first access
        factory = manager.session_factory
        assert factory is not None
        assert manager._session_factory is factory

        # Second access should return same factory
        assert manager.session_factory is factory


class TestBase:
    """Test suite for SQLAlchemy Base class."""

    def test_base_is_declarative_base(self) -> None:
        """Test Base is a proper DeclarativeBase."""
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")


class TestGetDatabaseManager:
    """Test suite for get_database_manager function."""

    def test_returns_database_manager(self) -> None:
        """Test get_database_manager returns a DatabaseManager instance."""
        manager = get_database_manager()
        assert isinstance(manager, DatabaseManager)

    def test_returns_same_instance(self) -> None:
        """Test get_database_manager returns the same instance (singleton)."""
        manager1 = get_database_manager()
        manager2 = get_database_manager()
        assert manager1 is manager2
