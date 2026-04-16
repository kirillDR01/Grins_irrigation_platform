"""Unit tests for BusinessSettingService (H-12).

Covers the typed helpers (``get_int`` / ``get_decimal`` / ``set_value``)
and verifies that ``set_value`` writes an audit-log row on every call.

These tests use an in-memory mock session — the service is thin enough
that we exercise the code paths directly via ``AsyncMock`` + a
hand-rolled fake query result.

Validates: bughunt 2026-04-16 finding H-12.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.services.business_setting_service import (
    BUSINESS_SETTING_KEYS,
    BusinessSettingService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(value: object | None) -> MagicMock:
    """Build a fake BusinessSetting ORM row with ``setting_value=value``."""
    row = MagicMock()
    row.id = uuid4()
    row.setting_value = value
    return row


def _make_session_with_existing_row(value: object | None) -> AsyncMock:
    """Return an AsyncMock session whose ``execute`` returns ``value``."""
    session = AsyncMock()

    async def _execute(_stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = _make_row(value)
        return result

    session.execute.side_effect = _execute
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


def _make_session_missing() -> AsyncMock:
    """Return an AsyncMock session whose lookups return None."""
    session = AsyncMock()

    async def _execute(_stmt):
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        return result

    session.execute.side_effect = _execute
    session.add = MagicMock()
    session.flush = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# get_int / get_decimal
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBusinessSettingServiceGetInt:
    """Typed int reader."""

    @pytest.mark.asyncio
    async def test_get_int_returns_value_when_key_exists(self) -> None:
        session = _make_session_with_existing_row({"value": 90})
        service = BusinessSettingService(session)
        result = await service.get_int("lien_days_past_due", default=60)
        assert result == 90

    @pytest.mark.asyncio
    async def test_get_int_returns_default_when_key_missing(self) -> None:
        session = _make_session_missing()
        service = BusinessSettingService(session)
        result = await service.get_int("nonexistent_h12", default=42)
        assert result == 42

    @pytest.mark.asyncio
    async def test_get_int_unwraps_legacy_bare_scalar(self) -> None:
        """Legacy seed rows store bare JSON literals, not dicts."""
        session = _make_session_with_existing_row(120)
        service = BusinessSettingService(session)
        result = await service.get_int("legacy_bare_int", default=60)
        assert result == 120

    @pytest.mark.asyncio
    async def test_get_int_falls_back_on_coerce_failure(self) -> None:
        session = _make_session_with_existing_row({"value": "not-a-number"})
        service = BusinessSettingService(session)
        result = await service.get_int("bad_value", default=7)
        assert result == 7

    @pytest.mark.asyncio
    async def test_get_int_falls_back_when_row_has_null_value(self) -> None:
        session = _make_session_with_existing_row(None)
        service = BusinessSettingService(session)
        result = await service.get_int("null_value", default=9)
        assert result == 9


@pytest.mark.unit
class TestBusinessSettingServiceGetDecimal:
    """Typed Decimal reader."""

    @pytest.mark.asyncio
    async def test_get_decimal_returns_value_when_key_exists(self) -> None:
        session = _make_session_with_existing_row({"value": "750.50"})
        service = BusinessSettingService(session)
        result = await service.get_decimal(
            "lien_min_amount",
            default=Decimal(500),
        )
        assert result == Decimal("750.50")

    @pytest.mark.asyncio
    async def test_get_decimal_returns_default_when_missing(self) -> None:
        session = _make_session_missing()
        service = BusinessSettingService(session)
        result = await service.get_decimal(
            "nonexistent_h12_decimal",
            default=Decimal(500),
        )
        assert result == Decimal(500)

    @pytest.mark.asyncio
    async def test_get_decimal_accepts_number(self) -> None:
        """``{"value": 500}`` is valid because str(500) parses cleanly."""
        session = _make_session_with_existing_row({"value": 500})
        service = BusinessSettingService(session)
        result = await service.get_decimal(
            "numeric_value",
            default=Decimal(123),
        )
        assert result == Decimal(500)


@pytest.mark.unit
class TestBusinessSettingServiceSetValue:
    """set_value CRUD + audit."""

    @pytest.mark.asyncio
    async def test_set_value_writes_audit_log(self) -> None:
        """set_value emits exactly one AuditLog row per call."""
        actor = uuid4()
        session = _make_session_missing()

        audit_repo_instance = MagicMock()
        audit_repo_instance.create = AsyncMock()

        service = BusinessSettingService(session)
        with patch(
            "grins_platform.services.business_setting_service.AuditLogRepository",
            return_value=audit_repo_instance,
        ) as mock_repo_cls:
            await service.set_value(
                "lien_days_past_due", 75, updated_by=actor,
            )

        mock_repo_cls.assert_called_once_with(session)
        audit_repo_instance.create.assert_awaited_once()
        call_kwargs = audit_repo_instance.create.await_args.kwargs
        assert call_kwargs["action"] == "business_setting.updated"
        assert call_kwargs["resource_type"] == "business_setting"
        assert call_kwargs["actor_id"] == actor
        assert call_kwargs["details"] == {
            "key": "lien_days_past_due",
            "value": 75,
        }

    @pytest.mark.asyncio
    async def test_set_value_inserts_when_row_missing(self) -> None:
        """A brand-new key results in session.add(...) being called once."""
        actor = uuid4()
        session = _make_session_missing()
        service = BusinessSettingService(session)

        audit_repo_instance = MagicMock()
        audit_repo_instance.create = AsyncMock()

        with patch(
            "grins_platform.services.business_setting_service.AuditLogRepository",
            return_value=audit_repo_instance,
        ):
            await service.set_value(
                "upcoming_due_days", 5, updated_by=actor,
            )

        # session.add should have been called with a new BusinessSetting.
        assert session.add.call_count == 1
        added = session.add.call_args[0][0]
        assert added.setting_key == "upcoming_due_days"
        assert added.setting_value == {"value": 5}

    @pytest.mark.asyncio
    async def test_set_value_updates_when_row_exists(self) -> None:
        """Existing rows are mutated in-place; session.add is NOT called."""
        actor = uuid4()
        existing = _make_row({"value": 3})
        session = AsyncMock()

        async def _execute(_stmt):
            result = MagicMock()
            result.scalar_one_or_none.return_value = existing
            return result

        session.execute.side_effect = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        audit_repo_instance = MagicMock()
        audit_repo_instance.create = AsyncMock()

        service = BusinessSettingService(session)
        with patch(
            "grins_platform.services.business_setting_service.AuditLogRepository",
            return_value=audit_repo_instance,
        ):
            await service.set_value(
                "upcoming_due_days", 14, updated_by=actor,
            )

        assert session.add.call_count == 0
        assert existing.setting_value == {"value": 14}
        assert existing.updated_by == actor

    @pytest.mark.asyncio
    async def test_set_value_is_idempotent(self) -> None:
        """Calling set_value twice for the same key never creates two rows."""
        actor = uuid4()
        existing = _make_row({"value": 0})
        session = AsyncMock()

        async def _execute(_stmt):
            result = MagicMock()
            result.scalar_one_or_none.return_value = existing
            return result

        session.execute.side_effect = _execute
        session.add = MagicMock()
        session.flush = AsyncMock()

        audit_repo_instance = MagicMock()
        audit_repo_instance.create = AsyncMock()

        service = BusinessSettingService(session)
        with patch(
            "grins_platform.services.business_setting_service.AuditLogRepository",
            return_value=audit_repo_instance,
        ):
            await service.set_value("lien_min_amount", "500", updated_by=actor)
            await service.set_value("lien_min_amount", "1000", updated_by=actor)

        assert session.add.call_count == 0
        assert existing.setting_value == {"value": "1000"}
        # Audit log fires on every call (2 total).
        assert audit_repo_instance.create.await_count == 2

    @pytest.mark.asyncio
    async def test_set_value_audit_failure_does_not_block_write(self) -> None:
        """Audit errors are swallowed so the value write still persists."""
        actor = uuid4()
        session = _make_session_missing()

        audit_repo_instance = MagicMock()
        audit_repo_instance.create = AsyncMock(
            side_effect=RuntimeError("audit table missing"),
        )

        service = BusinessSettingService(session)
        with patch(
            "grins_platform.services.business_setting_service.AuditLogRepository",
            return_value=audit_repo_instance,
        ):
            # Must not raise.
            await service.set_value(
                "confirmation_no_reply_days", 5, updated_by=actor,
            )

        # Value row still inserted.
        assert session.add.call_count == 1


@pytest.mark.unit
class TestBusinessSettingServiceGetAll:
    """get_all returns every known key."""

    @pytest.mark.asyncio
    async def test_get_all_returns_every_known_key(self) -> None:
        session = _make_session_missing()
        service = BusinessSettingService(session)
        values = await service.get_all()
        for key in BUSINESS_SETTING_KEYS:
            assert key in values
            assert values[key] is None
