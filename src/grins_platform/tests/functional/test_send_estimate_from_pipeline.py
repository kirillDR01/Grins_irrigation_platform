"""Functional tests for the Sales Pipeline structured-estimate endpoints.

Covers ``POST /api/v1/sales/pipeline/{entry_id}/send-estimate`` and
``/resend-estimate`` — the orchestrator endpoints that replace the legacy
SignWell PDF-upload flow on the ``send_estimate`` stage.

These tests exercise the endpoint coroutines directly with mocked
session + service dependencies, matching the project's functional-test
pattern (see ``test_sales_pipeline_functional.py``).

Validates: feature — sales-pipeline structured estimate + portal flow.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from grins_platform.api.v1.sales_pipeline import (
    resend_estimate_from_pipeline,
    send_estimate_from_pipeline,
)
from grins_platform.models.enums import EstimateStatus, SalesEntryStatus
from grins_platform.schemas.estimate import EstimateSendResponse
from grins_platform.schemas.sales_pipeline import SendEstimateFromPipelineRequest

# =============================================================================
# Helpers
# =============================================================================


def _make_customer(*, email: str | None = "kirillrakitinsecond@gmail.com") -> MagicMock:
    c = MagicMock()
    c.id = uuid4()
    c.email = email
    c.phone = "+19527373312"
    c.full_name = "Test Customer"
    c.first_name = "Test"
    c.last_name = "Customer"
    return c


def _make_entry(
    *,
    customer: MagicMock | None = None,
    status: str = SalesEntryStatus.SEND_ESTIMATE.value,
    customer_id: Any = None,
) -> MagicMock:
    entry = MagicMock()
    entry.id = uuid4()
    entry.customer_id = (
        customer_id
        if customer_id is not None
        else (customer.id if customer else uuid4())
    )
    entry.lead_id = None
    entry.status = status
    entry.customer = customer
    return entry


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    return user


def _scalar_result(value: Any) -> MagicMock:
    """Mock a SQLAlchemy ``Result`` whose ``scalar_one_or_none`` returns value."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_estimate_response(estimate_id: Any | None = None) -> MagicMock:
    est = MagicMock()
    est.id = estimate_id or uuid4()
    return est


def _build_send_request(**overrides: Any) -> SendEstimateFromPipelineRequest:
    return SendEstimateFromPipelineRequest(
        line_items=overrides.get(
            "line_items",
            [
                {
                    "description": "Spring Start-Up",
                    "quantity": 1,
                    "unit_price": 175.0,
                    "amount": 175.0,
                }
            ],
        ),
        subtotal=overrides.get("subtotal", Decimal(175)),
        total=overrides.get("total", Decimal(175)),
        notes=overrides.get("notes"),
    )


# =============================================================================
# send_estimate_from_pipeline
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestSendEstimateFromPipeline:
    async def test_send_estimate_happy_path(self) -> None:
        """Orchestrator: create + send + advance + audit + commit."""
        customer = _make_customer()
        entry = _make_entry(customer=customer)
        user = _make_user()

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[_scalar_result(entry), MagicMock()])
        session.commit = AsyncMock()

        estimate_response = _make_estimate_response()
        estimate_service = MagicMock()
        estimate_service.create_estimate = AsyncMock(return_value=estimate_response)
        estimate_service.send_estimate = AsyncMock(
            return_value=EstimateSendResponse(
                estimate_id=estimate_response.id,
                portal_url=f"http://localhost:5173/portal/estimates/{uuid4()}",
                sent_via=["sms", "email"],
            )
        )

        sales_pipeline_service = MagicMock()
        sales_pipeline_service.audit_service = MagicMock()
        sales_pipeline_service.audit_service.log_action = AsyncMock()

        body = _build_send_request()

        response = await send_estimate_from_pipeline(
            entry_id=entry.id,
            body=body,
            current_user=user,
            session=session,
            estimate_service=estimate_service,
            sales_pipeline_service=sales_pipeline_service,
        )

        assert response.entry_id == entry.id
        assert response.entry_status == SalesEntryStatus.PENDING_APPROVAL.value
        assert response.estimate_id == estimate_response.id
        assert response.portal_url.startswith("http://localhost:5173/portal/estimates/")
        assert response.sent_via == ["sms", "email"]

        estimate_service.create_estimate.assert_awaited_once()
        ec_args = estimate_service.create_estimate.await_args.args
        assert ec_args[0].customer_id == entry.customer_id
        assert ec_args[1] == user.id

        estimate_service.send_estimate.assert_awaited_once_with(estimate_response.id)

        # Audit row written with canonical kwargs
        sales_pipeline_service.audit_service.log_action.assert_awaited_once()
        audit_kwargs = sales_pipeline_service.audit_service.log_action.await_args.kwargs
        assert audit_kwargs["action"] == "sales_entry.estimate_sent"
        assert audit_kwargs["resource_type"] == "sales_entry"
        assert audit_kwargs["resource_id"] == entry.id
        assert audit_kwargs["actor_id"] == user.id
        assert "estimate_id" in audit_kwargs["details"]

        session.commit.assert_awaited_once()

    async def test_send_estimate_404_for_missing_entry(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        estimate_service = MagicMock()
        sales_pipeline_service = MagicMock()
        sales_pipeline_service.audit_service = MagicMock()

        with pytest.raises(HTTPException) as exc:
            await send_estimate_from_pipeline(
                entry_id=uuid4(),
                body=_build_send_request(),
                current_user=_make_user(),
                session=session,
                estimate_service=estimate_service,
                sales_pipeline_service=sales_pipeline_service,
            )
        assert exc.value.status_code == 404
        assert "Sales entry not found" in str(exc.value.detail)

    async def test_send_estimate_422_for_no_customer_email(self) -> None:
        customer = _make_customer(email=None)
        entry = _make_entry(customer=customer)

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(entry))

        estimate_service = MagicMock()
        sales_pipeline_service = MagicMock()
        sales_pipeline_service.audit_service = MagicMock()

        with pytest.raises(HTTPException) as exc:
            await send_estimate_from_pipeline(
                entry_id=entry.id,
                body=_build_send_request(),
                current_user=_make_user(),
                session=session,
                estimate_service=estimate_service,
                sales_pipeline_service=sales_pipeline_service,
            )
        assert exc.value.status_code == 422
        assert "no email address" in str(exc.value.detail)

    async def test_send_estimate_advances_even_if_calendar_unconfirmed(self) -> None:
        """Orchestrator bypasses the calendar-confirmation gate.

        Sending the estimate is itself the confirmation that the visit
        happened — we transition straight to ``pending_approval`` even
        when ``advance_status`` would have raised
        ``EstimateNotConfirmedError``.
        """
        customer = _make_customer()
        entry = _make_entry(customer=customer)
        user = _make_user()

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=[_scalar_result(entry), MagicMock()])
        session.commit = AsyncMock()

        estimate_response = _make_estimate_response()
        estimate_service = MagicMock()
        estimate_service.create_estimate = AsyncMock(return_value=estimate_response)
        estimate_service.send_estimate = AsyncMock(
            return_value=EstimateSendResponse(
                estimate_id=estimate_response.id,
                portal_url=f"http://localhost:5173/portal/estimates/{uuid4()}",
                sent_via=["email"],
            )
        )

        sales_pipeline_service = MagicMock()
        sales_pipeline_service.audit_service = MagicMock()
        sales_pipeline_service.audit_service.log_action = AsyncMock()

        response = await send_estimate_from_pipeline(
            entry_id=entry.id,
            body=_build_send_request(),
            current_user=user,
            session=session,
            estimate_service=estimate_service,
            sales_pipeline_service=sales_pipeline_service,
        )

        # Calendar event never queried at all by orchestrator path.
        assert response.entry_status == SalesEntryStatus.PENDING_APPROVAL.value
        # Two execute calls total: SELECT entry, UPDATE entry. No third
        # call to fetch a SalesCalendarEvent.
        assert session.execute.await_count == 2


# =============================================================================
# resend_estimate_from_pipeline
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestResendEstimateFromPipeline:
    async def test_resend_estimate_happy_path(self) -> None:
        customer = _make_customer()
        entry = _make_entry(customer=customer)

        latest_estimate = MagicMock()
        latest_estimate.id = uuid4()
        latest_estimate.status = EstimateStatus.SENT.value
        latest_estimate.updated_at = datetime.now(tz=timezone.utc)

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(entry),
                _scalar_result(latest_estimate),
            ]
        )
        session.commit = AsyncMock()

        estimate_service = MagicMock()
        estimate_service.send_estimate = AsyncMock(
            return_value=EstimateSendResponse(
                estimate_id=latest_estimate.id,
                portal_url=f"http://localhost:5173/portal/estimates/{uuid4()}",
                sent_via=["sms", "email"],
            )
        )

        result = await resend_estimate_from_pipeline(
            entry_id=entry.id,
            _current_user=_make_user(),
            session=session,
            estimate_service=estimate_service,
        )

        estimate_service.send_estimate.assert_awaited_once_with(latest_estimate.id)
        session.commit.assert_awaited_once()
        assert result.estimate_id == latest_estimate.id
        assert "email" in result.sent_via

    async def test_resend_estimate_404_when_no_open_estimate(self) -> None:
        customer = _make_customer()
        entry = _make_entry(customer=customer)

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[_scalar_result(entry), _scalar_result(None)]
        )

        estimate_service = MagicMock()
        estimate_service.send_estimate = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await resend_estimate_from_pipeline(
                entry_id=entry.id,
                _current_user=_make_user(),
                session=session,
                estimate_service=estimate_service,
            )
        assert exc.value.status_code == 404
        assert "No open estimate" in str(exc.value.detail)
        estimate_service.send_estimate.assert_not_awaited()

    async def test_resend_estimate_404_when_entry_missing(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        estimate_service = MagicMock()
        estimate_service.send_estimate = AsyncMock()

        with pytest.raises(HTTPException) as exc:
            await resend_estimate_from_pipeline(
                entry_id=uuid4(),
                _current_user=_make_user(),
                session=session,
                estimate_service=estimate_service,
            )
        assert exc.value.status_code == 404
        estimate_service.send_estimate.assert_not_awaited()
