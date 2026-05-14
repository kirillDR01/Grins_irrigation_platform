"""SettingsService for business settings management.

Provides get_all_settings() and update_setting() for the
business_settings table with in-memory caching.

Validates: CRM Gap Closure Req 87.2, 87.7, 87.8, 87.9
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.business_setting import BusinessSetting
from grins_platform.schemas.settings import BusinessSettingResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SettingNotFoundError(Exception):
    """Raised when a setting key is not found."""

    def __init__(self, key: str) -> None:
        super().__init__(f"Setting '{key}' not found")
        self.key = key


class SettingsService(LoggerMixin):
    """Service for business settings CRUD with caching.

    Reads/writes the business_settings table. Maintains an in-memory
    cache that is invalidated on updates.

    Validates: CRM Gap Closure Req 87.2, 87.7, 87.8, 87.9
    """

    DOMAIN = "settings"

    def __init__(self) -> None:
        """Initialize SettingsService with empty cache."""
        super().__init__()
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_loaded: bool = False

    def _invalidate_cache(self, key: str | None = None) -> None:
        """Invalidate the settings cache.

        Args:
            key: Specific key to invalidate, or None for all.
        """
        if key is not None:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
            self._cache_loaded = False

    async def get_all_settings(
        self,
        db: AsyncSession,
    ) -> list[BusinessSettingResponse]:
        """Retrieve all business settings.

        Uses in-memory cache when available.

        Args:
            db: Database session.

        Returns:
            List of BusinessSettingResponse.

        Validates: Req 87.2
        """
        self.log_started("get_all_settings")

        stmt = select(BusinessSetting).order_by(BusinessSetting.setting_key)
        result = await db.execute(stmt)
        settings = list(result.scalars().all())

        # Update cache
        self._cache.clear()
        for s in settings:
            self._cache[s.setting_key] = s.setting_value or {}
        self._cache_loaded = True

        items = [BusinessSettingResponse.model_validate(s) for s in settings]

        self.log_completed("get_all_settings", count=len(items))
        return items

    async def get_setting(
        self,
        db: AsyncSession,
        key: str,
    ) -> dict[str, Any]:
        """Retrieve a single setting value by key.

        Uses cache if available, otherwise queries DB.

        Args:
            db: Database session.
            key: Setting key.

        Returns:
            Setting value as dict.

        Raises:
            SettingNotFoundError: If key not found.

        Validates: Req 87.2
        """
        # Check cache first
        if self._cache_loaded and key in self._cache:
            return self._cache[key]

        stmt = select(BusinessSetting).where(
            BusinessSetting.setting_key == key,
        )
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()

        if setting is None:
            raise SettingNotFoundError(key)

        value = setting.setting_value or {}
        self._cache[key] = value
        return value

    async def update_setting(
        self,
        db: AsyncSession,
        *,
        key: str,
        value: dict[str, Any],
        updated_by: UUID | None = None,
    ) -> BusinessSettingResponse:
        """Update a business setting value.

        Args:
            db: Database session.
            key: Setting key.
            value: New setting value as dict.
            updated_by: Staff UUID who made the update.

        Returns:
            Updated BusinessSettingResponse.

        Raises:
            SettingNotFoundError: If key not found.

        Validates: Req 87.2
        """
        self.log_started("update_setting", key=key)

        stmt = select(BusinessSetting).where(
            BusinessSetting.setting_key == key,
        )
        result = await db.execute(stmt)
        setting = result.scalar_one_or_none()

        if setting is None:
            raise SettingNotFoundError(key)

        setting.setting_value = value
        setting.updated_by = updated_by
        setting.updated_at = datetime.now(tz=timezone.utc)
        await db.flush()
        await db.refresh(setting)

        # Invalidate cache for this key
        self._invalidate_cache(key)

        self.log_completed("update_setting", key=key)
        return BusinessSettingResponse.model_validate(setting)

    async def get_company_info(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Get company branding info for PDF generation and portal.

        Convenience method used by InvoicePDFService (Req 87.7).

        Args:
            db: Database session.

        Returns:
            Dict with company_name, company_address, company_phone,
            company_logo_url.
        """
        try:
            return await self.get_setting(db, "company_info")
        except SettingNotFoundError:
            return {
                "company_name": "Grin's Irrigation",
                "company_address": "",
                "company_phone": "",
                "company_logo_url": "",
            }

    async def get_notification_prefs(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Get notification preferences for NotificationService.

        Convenience method used by NotificationService (Req 87.8).

        Args:
            db: Database session.

        Returns:
            Dict with sms_window_start, sms_window_end,
            pre_due_reminder_days, past_due_interval_days, etc.
        """
        try:
            return await self.get_setting(db, "notification_prefs")
        except SettingNotFoundError:
            return {
                "sms_window_start": "08:00",
                "sms_window_end": "21:00",
                "pre_due_reminder_days": 3,
                "past_due_interval_days": 7,
                "lien_threshold_days": 30,
            }

    async def get_invoice_defaults(
        self,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Get invoice default settings.

        Args:
            db: Database session.

        Returns:
            Dict with payment_terms_days, late_fee_percentage, etc.
        """
        try:
            return await self.get_setting(db, "invoice_defaults")
        except SettingNotFoundError:
            return {
                "payment_terms_days": 30,
                "late_fee_percentage": 0,
                "lien_eligible_days": 90,
            }
