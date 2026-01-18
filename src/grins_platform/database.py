"""
Database configuration and connection management.

This module provides async database connection management using SQLAlchemy 2.0
with asyncpg for PostgreSQL. It includes connection pooling and session management.
"""

from collections.abc import AsyncGenerator
from typing import Any, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from grins_platform.log_config import LoggerMixin, get_logger

logger = get_logger(__name__)


class DatabaseSettings(BaseSettings):
    """Database configuration settings loaded from environment."""

    database_url: str = "postgresql://grins_user:grins_password@localhost:5432/grins_platform"

    # Connection pool settings
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30
    pool_recycle: int = 1800  # 30 minutes

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def async_database_url(self) -> str:
        """Convert database URL to async format for asyncpg."""
        url = self.database_url
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+asyncpg://", 1)
        return url


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""



class DatabaseManager(LoggerMixin):
    """Manages database connections and sessions."""

    DOMAIN = "database"

    def __init__(self, settings: Optional[DatabaseSettings] = None) -> None:
        """Initialize database manager with settings.

        Args:
            settings: Database settings, loads from environment if not provided
        """
        super().__init__()
        self.settings = settings or DatabaseSettings()
        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

    @property
    def engine(self) -> AsyncEngine:
        """Get or create the async database engine."""
        if self._engine is None:
            self._engine = create_async_engine(
                self.settings.async_database_url,
                pool_size=self.settings.pool_size,
                max_overflow=self.settings.max_overflow,
                pool_timeout=self.settings.pool_timeout,
                pool_recycle=self.settings.pool_recycle,
                echo=False,  # Set to True for SQL debugging
            )
            self.log_completed(
                "engine_created",
                pool_size=self.settings.pool_size,
                max_overflow=self.settings.max_overflow,
            )
        return self._engine

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Get or create the session factory."""
        if self._session_factory is None:
            self._session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        return self._session_factory

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session.

        Yields:
            AsyncSession: Database session for executing queries
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        """Close the database engine and all connections."""
        if self._engine is not None:
            self.log_started("connection_close")
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            self.log_completed("connection_close")

    async def health_check(self) -> dict[str, Any]:
        """Check database connectivity.

        Returns:
            dict with health status information
        """
        self.log_started("health_check")
        try:
            async with self.session_factory() as session:
                result = await session.execute(text("SELECT 1"))
                _ = result.scalar()
        except Exception as e:
            self.log_failed("health_check", error=e)
            return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
        else:
            self.log_completed("health_check", status="healthy")
            return {"status": "healthy", "database": "connected"}


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_database_manager() -> DatabaseManager:
    """Get the global database manager instance.

    Returns:
        DatabaseManager: The global database manager
    """
    global _db_manager  # noqa: PLW0603
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions in FastAPI.

    Yields:
        AsyncSession: Database session
    """
    db_manager = get_database_manager()
    async for session in db_manager.get_session():
        yield session
