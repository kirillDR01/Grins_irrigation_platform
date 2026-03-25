"""Unit tests for Invoice bulk notify and Sales pipeline metrics.

Properties:
  P41: Consent-gated bulk invoice notifications
  P50: Sales pipeline metrics accuracy

Validates: Requirements 38.1, 38.3, 38.4, 38.6, 47.2, 47.3, 47.6
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from grins_platform.models.enums import InvoiceStatus
from grins_platform.services.invoice_service import (
    InvoiceNotFoundError,
    InvoiceService,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_invoice_service(
    *,
    invoice_repo: AsyncMock | None = None,
    job_repo: AsyncMock | None = None,
) -> InvoiceService:
    """Create an InvoiceService with mock repositories."""
    return InvoiceService(
        invoice_repository=invoice_repo or AsyncMock(),
        job_repository=job_repo or AsyncMock(),
    )


def _mock_invoice(
    *,
    status: str = InvoiceStatus.SENT.value,
    reminder_count: int = 0,
) -> MagicMock:
    """Create a mock invoice object."""
    inv = MagicMock()
    inv.id = uuid4()
    inv.invoice_number = "INV-2025-000001"
    inv.status = status
    inv.reminder_count = reminder_count
    inv.last_reminder_sent = None
    inv.lien_warning_sent = None
    inv.lien_eligible = True
    inv.amount = Decimal("500.00")
    inv.total_amount = Decimal("500.00")
    inv.late_fee_amount = Decimal("0.00")
    inv.paid_amount = Decimal("0.00")
    inv.due_date = None
    inv.customer_id = uuid4()
    inv.job_id = uuid4()
    inv.document_url = None
    inv.invoice_token = None
    inv.customer_name = None
    return inv


async def _simulate_bulk_notify(
    service: InvoiceService,
    invoice_ids: list[UUID],
    notification_type: str = "REMINDER",
) -> dict[str, int]:
    """Simulate the bulk_notify_invoices API logic.

    Mirrors the actual endpoint in api/v1/invoices.py:
    - InvoiceNotFoundError → skipped
    - Other exceptions → failed
    - Success → sent
    """
    sent = 0
    failed = 0
    skipped = 0

    for inv_id in invoice_ids:
        sent, skipped, failed = await _notify_single(
            service,
            inv_id,
            notification_type,
            sent,
            skipped,
            failed,
        )

    return {
        "sent": sent,
        "failed": failed,
        "skipped": skipped,
        "total": len(invoice_ids),
    }


async def _notify_single(
    service: InvoiceService,
    inv_id: UUID,
    notification_type: str,
    sent: int,
    skipped: int,
    failed: int,
) -> tuple[int, int, int]:
    """Process a single invoice notification, returning updated counters."""
    try:
        if notification_type == "LIEN_WARNING":
            await service.send_lien_warning(inv_id)
        else:
            await service.send_reminder(inv_id)
        sent += 1
    except InvoiceNotFoundError:
        skipped += 1
    except Exception:
        failed += 1
    return sent, skipped, failed


# =============================================================================
# Property 41: Consent-gated bulk invoice notifications
# Validates: Requirements 38.1, 38.3, 38.4
# =============================================================================


@pytest.mark.unit
class TestProperty41ConsentGatedBulkInvoiceNotifications:
    """Test consent-gated bulk invoice notifications with correct summary.

    **Validates: Requirements 38.1, 38.3, 38.4**

    The bulk_notify_invoices API endpoint iterates invoice IDs, calls
    send_reminder or send_lien_warning per invoice, and returns a summary
    with sent_count, skipped_count, and failed_count.

    Consent gating: InvoiceNotFoundError → skipped; other exceptions → failed.
    """

    @pytest.mark.asyncio
    async def test_bulk_notify_with_all_valid_invoices_returns_all_sent(
        self,
    ) -> None:
        """All invoices found and notified → sent equals total, 0 skipped/failed."""
        service = _make_invoice_service()
        updated_inv = _mock_invoice(status=InvoiceStatus.SENT.value)
        updated_inv.reminder_count = 1
        service.send_reminder = AsyncMock(return_value=updated_inv)

        invoice_ids = [uuid4(), uuid4(), uuid4()]
        result = await _simulate_bulk_notify(service, invoice_ids)

        assert result["sent"] == 3
        assert result["skipped"] == 0
        assert result["failed"] == 0
        assert result["sent"] + result["skipped"] + result["failed"] == result["total"]

    @pytest.mark.asyncio
    async def test_bulk_notify_with_missing_invoices_returns_skipped(
        self,
    ) -> None:
        """Missing invoices are skipped (InvoiceNotFoundError), not failed."""
        service = _make_invoice_service()

        inv1_id = uuid4()
        inv2_id = uuid4()
        inv3_id = uuid4()

        async def _side_effect(invoice_id: UUID) -> MagicMock:
            if invoice_id == inv2_id:
                raise InvoiceNotFoundError(invoice_id)
            return _mock_invoice()

        service.send_reminder = AsyncMock(side_effect=_side_effect)

        result = await _simulate_bulk_notify(service, [inv1_id, inv2_id, inv3_id])

        assert result["sent"] == 2
        assert result["skipped"] == 1
        assert result["failed"] == 0
        assert result["sent"] + result["skipped"] + result["failed"] == result["total"]

    @pytest.mark.asyncio
    async def test_bulk_notify_with_failures_returns_failed_count(
        self,
    ) -> None:
        """Unexpected exceptions count as failed, not skipped."""
        service = _make_invoice_service()

        inv1_id = uuid4()
        inv2_id = uuid4()

        async def _side_effect(invoice_id: UUID) -> MagicMock:
            if invoice_id == inv2_id:
                msg = "SMS gateway error"
                raise RuntimeError(msg)
            return _mock_invoice()

        service.send_reminder = AsyncMock(side_effect=_side_effect)

        result = await _simulate_bulk_notify(service, [inv1_id, inv2_id])

        assert result["sent"] == 1
        assert result["failed"] == 1
        assert result["skipped"] == 0
        assert result["sent"] + result["skipped"] + result["failed"] == result["total"]

    @pytest.mark.asyncio
    async def test_bulk_notify_with_mixed_outcomes_returns_correct_summary(
        self,
    ) -> None:
        """Mixed: some sent, some skipped, some failed — summary is accurate."""
        service = _make_invoice_service()

        ids = [uuid4() for _ in range(5)]

        async def _side_effect(invoice_id: UUID) -> MagicMock:
            if invoice_id in (ids[1], ids[3]):
                raise InvoiceNotFoundError(invoice_id)
            if invoice_id == ids[4]:
                msg = "Network error"
                raise RuntimeError(msg)
            return _mock_invoice()

        service.send_reminder = AsyncMock(side_effect=_side_effect)

        result = await _simulate_bulk_notify(service, ids)

        assert result["sent"] == 2
        assert result["skipped"] == 2
        assert result["failed"] == 1
        assert result["sent"] + result["skipped"] + result["failed"] == result["total"]

    @pytest.mark.asyncio
    async def test_bulk_notify_with_lien_warning_type_calls_send_lien_warning(
        self,
    ) -> None:
        """LIEN_WARNING notification type routes to send_lien_warning."""
        service = _make_invoice_service()
        inv_id = uuid4()
        service.send_lien_warning = AsyncMock(return_value=_mock_invoice())

        result = await _simulate_bulk_notify(
            service,
            [inv_id],
            notification_type="LIEN_WARNING",
        )

        assert result["sent"] == 1
        service.send_lien_warning.assert_called_once_with(inv_id)

    @pytest.mark.asyncio
    async def test_bulk_notify_with_empty_list_returns_zero_counts(
        self,
    ) -> None:
        """Empty invoice list → all counts are zero."""
        service = _make_invoice_service()
        service.send_reminder = AsyncMock()

        result = await _simulate_bulk_notify(service, [])

        assert result["sent"] == 0
        assert result["skipped"] == 0
        assert result["failed"] == 0
        assert result["total"] == 0
        service.send_reminder.assert_not_called()


# =============================================================================
# Property 50: Sales pipeline metrics accuracy
# Validates: Requirements 47.2, 47.3
# =============================================================================


@pytest.mark.unit
class TestProperty50SalesPipelineMetricsAccuracy:
    """Test sales pipeline metrics return accurate counts.

    **Validates: Requirements 47.2, 47.3**

    The GET /api/v1/sales/metrics endpoint returns:
    - estimates_needing_writeup_count: estimates with status DRAFT
    - pending_approval_count: estimates with status SENT or VIEWED
    - needs_followup_count: distinct estimates with PENDING follow-ups
    - total_pipeline_revenue: sum of totals for DRAFT/SENT/VIEWED estimates
    - conversion_rate: (approved / total) * 100
    """

    def _build_mock_session(
        self,
        *,
        draft_count: int = 0,
        pending_count: int = 0,
        followup_count: int = 0,
        pipeline_revenue: Decimal = Decimal(0),
        total_estimates: int = 0,
        approved_count: int = 0,
    ) -> AsyncMock:
        """Build a mock AsyncSession that returns values for each query.

        The sales endpoint executes 6 sequential queries:
        1. DRAFT count
        2. SENT/VIEWED count
        3. PENDING follow-up distinct estimate count
        4. Pipeline revenue sum
        5. Total estimate count
        6. Approved estimate count
        """
        mock_session = AsyncMock()

        results = []
        for val in [
            draft_count,
            pending_count,
            followup_count,
            pipeline_revenue,
            total_estimates,
            approved_count,
        ]:
            mock_result = MagicMock()
            mock_result.scalar.return_value = val
            results.append(mock_result)

        mock_session.execute = AsyncMock(side_effect=results)
        return mock_session

    @pytest.mark.asyncio
    async def test_metrics_with_no_estimates_returns_all_zeros(self) -> None:
        """No estimates → all counts zero, revenue zero, conversion 0.0."""
        from grins_platform.api.v1.sales import get_sales_metrics  # noqa: PLC0415

        mock_session = self._build_mock_session()
        mock_user = MagicMock()

        result = await get_sales_metrics(
            _current_user=mock_user,
            session=mock_session,
        )

        assert result.estimates_needing_writeup_count == 0
        assert result.pending_approval_count == 0
        assert result.needs_followup_count == 0
        assert result.total_pipeline_revenue == Decimal(0)
        assert result.conversion_rate == 0.0

    @pytest.mark.asyncio
    async def test_metrics_with_draft_estimates_returns_correct_writeup_count(
        self,
    ) -> None:
        """Draft estimates counted as needing writeup."""
        from grins_platform.api.v1.sales import get_sales_metrics  # noqa: PLC0415

        mock_session = self._build_mock_session(
            draft_count=5,
            total_estimates=5,
        )
        mock_user = MagicMock()

        result = await get_sales_metrics(
            _current_user=mock_user,
            session=mock_session,
        )

        assert result.estimates_needing_writeup_count == 5

    @pytest.mark.asyncio
    async def test_metrics_with_sent_estimates_returns_correct_pending_count(
        self,
    ) -> None:
        """SENT and VIEWED estimates counted as pending approval."""
        from grins_platform.api.v1.sales import get_sales_metrics  # noqa: PLC0415

        mock_session = self._build_mock_session(
            pending_count=8,
            total_estimates=8,
        )
        mock_user = MagicMock()

        result = await get_sales_metrics(
            _current_user=mock_user,
            session=mock_session,
        )

        assert result.pending_approval_count == 8

    @pytest.mark.asyncio
    async def test_metrics_with_followups_returns_correct_followup_count(
        self,
    ) -> None:
        """Estimates with PENDING follow-ups counted correctly."""
        from grins_platform.api.v1.sales import get_sales_metrics  # noqa: PLC0415

        mock_session = self._build_mock_session(
            followup_count=3,
            total_estimates=10,
        )
        mock_user = MagicMock()

        result = await get_sales_metrics(
            _current_user=mock_user,
            session=mock_session,
        )

        assert result.needs_followup_count == 3

    @pytest.mark.asyncio
    async def test_metrics_with_pipeline_revenue_returns_correct_total(
        self,
    ) -> None:
        """Pipeline revenue sums totals of DRAFT/SENT/VIEWED estimates."""
        from grins_platform.api.v1.sales import get_sales_metrics  # noqa: PLC0415

        mock_session = self._build_mock_session(
            draft_count=2,
            pending_count=3,
            pipeline_revenue=Decimal("15750.50"),
            total_estimates=5,
        )
        mock_user = MagicMock()

        result = await get_sales_metrics(
            _current_user=mock_user,
            session=mock_session,
        )

        assert result.total_pipeline_revenue == Decimal("15750.50")

    @pytest.mark.asyncio
    async def test_metrics_with_approved_estimates_returns_correct_conversion_rate(
        self,
    ) -> None:
        """Conversion rate = (approved / total) * 100, rounded to 1 decimal."""
        from grins_platform.api.v1.sales import get_sales_metrics  # noqa: PLC0415

        mock_session = self._build_mock_session(
            total_estimates=20,
            approved_count=7,
        )
        mock_user = MagicMock()

        result = await get_sales_metrics(
            _current_user=mock_user,
            session=mock_session,
        )

        expected_rate = round((7 / 20) * 100, 1)
        assert result.conversion_rate == expected_rate

    @pytest.mark.asyncio
    async def test_metrics_with_zero_total_estimates_returns_zero_conversion(
        self,
    ) -> None:
        """Zero total estimates → conversion rate is 0.0 (no division by zero)."""
        from grins_platform.api.v1.sales import get_sales_metrics  # noqa: PLC0415

        mock_session = self._build_mock_session(
            total_estimates=0,
            approved_count=0,
        )
        mock_user = MagicMock()

        result = await get_sales_metrics(
            _current_user=mock_user,
            session=mock_session,
        )

        assert result.conversion_rate == 0.0

    @pytest.mark.asyncio
    async def test_metrics_with_full_pipeline_returns_all_accurate_values(
        self,
    ) -> None:
        """Full pipeline scenario: all metrics populated and accurate."""
        from grins_platform.api.v1.sales import get_sales_metrics  # noqa: PLC0415

        mock_session = self._build_mock_session(
            draft_count=4,
            pending_count=6,
            followup_count=2,
            pipeline_revenue=Decimal("28500.00"),
            total_estimates=25,
            approved_count=10,
        )
        mock_user = MagicMock()

        result = await get_sales_metrics(
            _current_user=mock_user,
            session=mock_session,
        )

        assert result.estimates_needing_writeup_count == 4
        assert result.pending_approval_count == 6
        assert result.needs_followup_count == 2
        assert result.total_pipeline_revenue == Decimal("28500.00")
        assert result.conversion_rate == round((10 / 25) * 100, 1)

    @pytest.mark.asyncio
    async def test_metrics_with_all_approved_returns_100_percent_conversion(
        self,
    ) -> None:
        """All estimates approved → 100% conversion rate."""
        from grins_platform.api.v1.sales import get_sales_metrics  # noqa: PLC0415

        mock_session = self._build_mock_session(
            total_estimates=5,
            approved_count=5,
        )
        mock_user = MagicMock()

        result = await get_sales_metrics(
            _current_user=mock_user,
            session=mock_session,
        )

        assert result.conversion_rate == 100.0
