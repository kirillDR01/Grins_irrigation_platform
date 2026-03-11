"""Repository for ConsentLanguageVersion database operations.

Append-only — no update or delete methods.

Validates: Requirements 11.1, 11.3
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.consent_language_version import ConsentLanguageVersion

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ConsentLanguageVersionRepository(LoggerMixin):
    """Repository for ConsentLanguageVersion database operations.

    Append-only — no update or delete methods.

    Validates: Requirements 11.1, 11.3
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def get_by_version(self, version: str) -> ConsentLanguageVersion | None:
        """Get a consent language version by version string.

        Validates: Requirement 11.1
        """
        self.log_started("get_by_version", version=version)
        stmt = select(ConsentLanguageVersion).where(
            ConsentLanguageVersion.version == version,
        )
        result = await self.session.execute(stmt)
        record: ConsentLanguageVersion | None = result.scalar_one_or_none()
        self.log_completed("get_by_version", found=record is not None)
        return record

    async def get_active_version(self) -> ConsentLanguageVersion | None:
        """Get the latest non-deprecated consent language version.

        Validates: Requirement 11.3
        """
        self.log_started("get_active_version")
        stmt = (
            select(ConsentLanguageVersion)
            .where(ConsentLanguageVersion.deprecated_date.is_(None))
            .order_by(ConsentLanguageVersion.effective_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        record: ConsentLanguageVersion | None = result.scalar_one_or_none()
        self.log_completed("get_active_version", found=record is not None)
        return record

    async def create(
        self,
        version: str,
        consent_text: str,
        effective_date: date,
    ) -> ConsentLanguageVersion:
        """Create a new consent language version record.

        Validates: Requirement 11.1
        """
        self.log_started("create", version=version)
        record = ConsentLanguageVersion(
            version=version,
            consent_text=consent_text,
            effective_date=effective_date,
        )
        self.session.add(record)
        await self.session.flush()
        self.log_completed("create", version=version, record_id=str(record.id))
        return record
