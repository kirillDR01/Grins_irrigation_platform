"""Unit tests for Gap 06 informal-opt-out Alert creation + auto-ack.

Validates:
- `_flag_informal_opt_out` creates an `Alert(type='informal_opt_out')` row
  with `entity_type='customer'` when the phone resolves, and
  `entity_type='phone'` when it does not.
- Alert creation failure does NOT break the inbound response.
- Subsequent exact STOP after informal auto-acknowledges the pending alert.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import AlertSeverity, AlertType
from grins_platform.services.sms_service import SMSService


def _make_service() -> SMSService:
    session = AsyncMock()
    session.execute = AsyncMock()
    session.add = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return SMSService(session)


@pytest.mark.unit
class TestInformalOptOutCreatesAlert:
    """Unit tests for Alert creation from `_flag_informal_opt_out`."""

    @pytest.mark.asyncio
    async def test_creates_alert_for_resolved_customer(self) -> None:
        """When phone resolves to a Customer, alert carries entity_type='customer'."""
        service = _make_service()
        customer_id = uuid4()
        saved_id = uuid4()

        async def _fake_create(alert):  # type: ignore[no-untyped-def]
            alert.id = saved_id
            return alert

        with (
            patch.object(
                service,
                "_resolve_customer_id_by_phone",
                new=AsyncMock(return_value=customer_id),
            ),
            patch(
                "grins_platform.services.sms_service.AlertRepository",
            ) as repo_cls,
        ):
            repo_cls.return_value.create = AsyncMock(side_effect=_fake_create)
            with patch(
                "grins_platform.services.sms_service.log_informal_opt_out_flagged",
                new=AsyncMock(),
            ) as log_mock:
                result = await service._flag_informal_opt_out(
                    "+16125551234",
                    "please stop texting me",
                )

        assert result["action"] == "informal_opt_out_flagged"
        assert result["alert_id"] == str(saved_id)
        created_alert = repo_cls.return_value.create.await_args[0][0]
        assert created_alert.type == AlertType.INFORMAL_OPT_OUT.value
        assert created_alert.severity == AlertSeverity.WARNING.value
        assert created_alert.entity_type == "customer"
        assert created_alert.entity_id == customer_id
        log_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creates_alert_with_phone_entity_when_unresolved(self) -> None:
        """Unresolved phones fall back to entity_type='phone' with a random UUID."""
        service = _make_service()
        saved_id = uuid4()

        async def _fake_create(alert):  # type: ignore[no-untyped-def]
            alert.id = saved_id
            return alert

        with (
            patch.object(
                service,
                "_resolve_customer_id_by_phone",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "grins_platform.services.sms_service.AlertRepository",
            ) as repo_cls,
        ):
            repo_cls.return_value.create = AsyncMock(side_effect=_fake_create)
            with patch(
                "grins_platform.services.sms_service.log_informal_opt_out_flagged",
                new=AsyncMock(),
            ):
                result = await service._flag_informal_opt_out(
                    "+16125551234",
                    "take me off the list",
                )

        assert result["action"] == "informal_opt_out_flagged"
        created_alert = repo_cls.return_value.create.await_args[0][0]
        assert created_alert.entity_type == "phone"
        assert created_alert.entity_id is not None

    @pytest.mark.asyncio
    async def test_alert_creation_failure_does_not_break_inbound(self) -> None:
        """If Alert insert raises, the inbound still returns a sensible result."""
        service = _make_service()

        with (
            patch.object(
                service,
                "_resolve_customer_id_by_phone",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "grins_platform.services.sms_service.AlertRepository",
            ) as repo_cls,
        ):
            repo_cls.return_value.create = AsyncMock(
                side_effect=RuntimeError("db down"),
            )
            result = await service._flag_informal_opt_out(
                "+16125551234",
                "opt out",
            )

        assert result["action"] == "informal_opt_out_flagged"
        assert result.get("alert_id") is None

    @pytest.mark.asyncio
    async def test_body_snippet_truncated_to_200(self) -> None:
        """Alert message truncates to 200 chars of body."""
        service = _make_service()
        long_body = "stop texting me " + ("x" * 500)
        saved_id = uuid4()

        async def _fake_create(alert):  # type: ignore[no-untyped-def]
            alert.id = saved_id
            return alert

        with (
            patch.object(
                service,
                "_resolve_customer_id_by_phone",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "grins_platform.services.sms_service.AlertRepository",
            ) as repo_cls,
        ):
            repo_cls.return_value.create = AsyncMock(side_effect=_fake_create)
            with patch(
                "grins_platform.services.sms_service.log_informal_opt_out_flagged",
                new=AsyncMock(),
            ):
                await service._flag_informal_opt_out("+16125551234", long_body)

        created_alert = repo_cls.return_value.create.await_args[0][0]
        snippet = long_body[:200]
        assert snippet in created_alert.message


@pytest.mark.unit
class TestAutoAckPendingInformalAlerts:
    """Unit tests for `_auto_ack_pending_informal_alerts`."""

    @pytest.mark.asyncio
    async def test_no_open_alerts_is_noop(self) -> None:
        """No pending alerts → no acknowledge, no audit."""
        service = _make_service()
        scalars = SimpleNamespace(all=list)
        service.session.execute.return_value = SimpleNamespace(scalars=lambda: scalars)

        with patch(
            "grins_platform.services.sms_service.log_informal_opt_out_auto_acknowledged",
            new=AsyncMock(),
        ) as log_mock:
            await service._auto_ack_pending_informal_alerts(uuid4())

        log_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_acknowledges_each_open_alert_and_audits(self) -> None:
        """Each open alert is acknowledged + audit event emitted."""
        service = _make_service()
        alert_a = SimpleNamespace(id=uuid4(), acknowledged_at=None)
        alert_b = SimpleNamespace(id=uuid4(), acknowledged_at=None)
        scalars = SimpleNamespace(all=lambda: [alert_a, alert_b])
        service.session.execute.return_value = SimpleNamespace(scalars=lambda: scalars)

        ack_mock = AsyncMock(side_effect=[alert_a, alert_b])
        with patch(
            "grins_platform.services.sms_service.AlertRepository",
        ) as repo_cls:
            repo_cls.return_value.acknowledge = ack_mock
            with patch(
                "grins_platform.services.sms_service."
                "log_informal_opt_out_auto_acknowledged",
                new=AsyncMock(),
            ) as log_mock:
                customer_id = uuid4()
                await service._auto_ack_pending_informal_alerts(customer_id)

        assert ack_mock.await_count == 2
        assert log_mock.await_count == 2
