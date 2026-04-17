"""BusinessSettingService — typed helpers over the ``business_settings`` table.

Provides ``get_int`` / ``get_decimal`` / ``set_value`` for consumers that need
firm-wide knobs (lien thresholds, SMS window, etc.). Writes an ``AuditLog`` row
on every ``set_value`` call so the admin audit trail captures the change.

This is deliberately narrower than :class:`SettingsService` — SettingsService
returns whole-dict domain values (``company_info``, ``notification_prefs``),
whereas BusinessSettingService stores one value per key. H-12 uses it for
four firm-wide knobs:

- ``lien_days_past_due`` — min age before an invoice is lien-eligible
- ``lien_min_amount`` — min $ past due before lien candidate
- ``upcoming_due_days`` — window used by mass-notify "due-soon"
- ``confirmation_no_reply_days`` — days until the no-reply review queue
  picks it up (H-7)

Validates: bughunt 2026-04-16 finding H-12.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.business_setting import BusinessSetting
from grins_platform.repositories.audit_log_repository import AuditLogRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# Keys owned by this service. Used by the API layer to list / return the
# "business settings" view for the admin panel.
BUSINESS_SETTING_KEYS: tuple[str, ...] = (
    "lien_days_past_due",
    "lien_min_amount",
    "upcoming_due_days",
    "confirmation_no_reply_days",
)


class BusinessSettingService(LoggerMixin):
    """Typed CRUD over ``business_settings`` for firm-wide knobs.

    Unlike :class:`SettingsService` (dict-valued domain settings), this
    service stores one scalar per key, mapped to ``{"value": <scalar>}``
    inside the ``setting_value`` JSONB column.

    Validates: bughunt 2026-04-16 finding H-12.
    """

    DOMAIN = "settings"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize service bound to a DB session.

        Args:
            session: Live :class:`AsyncSession` (request-scoped).
        """
        super().__init__()
        self.session = session

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _get_raw(self, key: str) -> Any:  # noqa: ANN401 — JSONB scalar can be any JSON primitive
        """Return the scalar stored under ``key`` or ``None`` if missing.

        The table stores values as ``{"value": <scalar>}``. Legacy keys
        written by seed data with a bare JSON literal (e.g. ``'60'``) are
        accepted too — we unwrap either shape transparently.

        Any unexpected error (missing table, mock session in unit tests,
        etc.) falls back to ``None`` so the caller uses the hard-coded
        default. We log the failure for visibility without blocking the
        calling flow.
        """
        try:
            stmt = select(BusinessSetting).where(
                BusinessSetting.setting_key == key,
            )
            result = await self.session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                return None
            raw = row.setting_value
            if raw is None:
                return None
            # Dict with a "value" key (new shape).
            if isinstance(raw, dict) and "value" in raw:
                return raw["value"]
            # Legacy scalar JSON literals (number, string, bool) round-trip
            # as the bare Python value via JSONB.
        except Exception:
            self.logger.warning(
                "business_setting.get_raw.lookup_failed",
                key=key,
            )
            return None
        else:
            return raw

    # ------------------------------------------------------------------
    # Typed getters
    # ------------------------------------------------------------------

    async def get_int(self, key: str, default: int) -> int:
        """Get an integer setting by key, falling back to ``default``.

        Args:
            key: Setting key.
            default: Returned verbatim if the row is missing or the value
                can't be coerced to ``int``.

        Returns:
            Integer value (or ``default``).
        """
        raw = await self._get_raw(key)
        if raw is None:
            return default
        try:
            return int(raw)
        except (TypeError, ValueError):
            self.logger.warning(
                "business_setting.get_int.coerce_failed",
                key=key,
                raw=str(raw),
            )
            return default

    async def get_decimal(self, key: str, default: Decimal) -> Decimal:
        """Get a Decimal setting by key, falling back to ``default``.

        Args:
            key: Setting key.
            default: Returned verbatim if the row is missing or the value
                can't be coerced to :class:`Decimal`.

        Returns:
            Decimal value (or ``default``).
        """
        raw = await self._get_raw(key)
        if raw is None:
            return default
        try:
            return Decimal(str(raw))
        except (InvalidOperation, TypeError, ValueError):
            self.logger.warning(
                "business_setting.get_decimal.coerce_failed",
                key=key,
                raw=str(raw),
            )
            return default

    async def get_all(self) -> dict[str, Any]:
        """Return every ``BUSINESS_SETTING_KEYS`` value as a flat dict.

        Missing keys are reported as ``None`` so the admin panel can render
        a placeholder.
        """
        out: dict[str, Any] = {}
        for key in BUSINESS_SETTING_KEYS:
            out[key] = await self._get_raw(key)
        return out

    # ------------------------------------------------------------------
    # Writer
    # ------------------------------------------------------------------

    async def set_value(
        self,
        key: str,
        value: Any,  # noqa: ANN401 — JSONB scalar can be any primitive
        updated_by: UUID | None,
    ) -> None:
        """Persist ``value`` under ``key`` (upsert) and emit an audit row.

        If the row already exists, the scalar is overwritten. If it does
        not, a new row is inserted. An ``AuditLog`` row with
        ``action="business_setting.updated"`` is always written — auditing
        is non-fatal but logged.

        Args:
            key: Setting key.
            value: Scalar JSON-serializable value.
            updated_by: Staff UUID responsible for the change (or None).
        """
        self.log_started("set_value", key=key)

        stmt = select(BusinessSetting).where(BusinessSetting.setting_key == key)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()

        payload: dict[str, Any] = {"value": value}

        if row is None:
            row = BusinessSetting(
                setting_key=key,
                setting_value=payload,
                updated_by=updated_by,
            )
            self.session.add(row)
        else:
            row.setting_value = payload
            row.updated_by = updated_by
            row.updated_at = datetime.now(timezone.utc)

        await self.session.flush()

        # Audit: always best-effort, never blocks the write.
        try:
            audit_repo = AuditLogRepository(self.session)
            await audit_repo.create(
                action="business_setting.updated",
                resource_type="business_setting",
                resource_id=row.id,
                actor_id=updated_by,
                details={
                    "key": key,
                    "value": value,
                },
            )
        except Exception:
            self.log_failed("set_value_audit", key=key)

        self.log_completed("set_value", key=key)
