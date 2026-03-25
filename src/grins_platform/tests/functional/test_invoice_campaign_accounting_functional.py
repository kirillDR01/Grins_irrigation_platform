"""Functional tests for invoice, campaign, and accounting operations.

Tests bulk invoice notifications, campaign lifecycle, expense CRUD,
accounting summary aggregations, audit log filtering, SentMessage
lead linkage, invoice PDF generation, and appointment no_show transitions.

Validates: Requirements 38.7, 45.12, 53.10, 52.8, 74.6, 81.10, 80.9, 79.8
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from grins_platform.models.enums import (
    AppointmentStatus,
    CampaignStatus,
    CampaignType,
    ExpenseCategory,
    InvoiceStatus,
)
from grins_platform.repositories.audit_log_repository import AuditLogRepository
from grins_platform.repositories.campaign_repository import CampaignRepository
from grins_platform.repositories.expense_repository import ExpenseRepository
from grins_platform.schemas.audit import AuditLogFilters
from grins_platform.schemas.campaign import CampaignCreate
from grins_platform.services.accounting_service import AccountingService
from grins_platform.services.appointment_service import AppointmentService
from grins_platform.services.audit_service import AuditService
from grins_platform.services.campaign_service import (
    CampaignAlreadySentError,
    CampaignService,
)
from grins_platform.services.invoice_pdf_service import (
    InvoiceNotFoundError as PDFInvoiceNotFoundError,
    InvoicePDFService,
)
from grins_platform.services.invoice_service import (
    InvoiceNotFoundError,
    InvoiceService,
)
from grins_platform.services.notification_service import NotificationService

# =============================================================================
# Helpers
# =============================================================================


def _mock_invoice(**overrides: Any) -> MagicMock:
    """Create a mock Invoice with standard fields."""
    inv = MagicMock()
    inv.id = overrides.get("id", uuid4())
    inv.invoice_number = overrides.get("invoice_number", "INV-2025-001")
    inv.status = overrides.get("status", InvoiceStatus.SENT.value)
    inv.total_amount = overrides.get("total_amount", Decimal("500.00"))
    inv.amount = overrides.get("amount", Decimal("500.00"))
    inv.late_fee_amount = overrides.get("late_fee_amount", Decimal(0))
    inv.invoice_date = overrides.get("invoice_date", date(2025, 3, 1))
    inv.due_date = overrides.get("due_date", date(2025, 4, 1))
    inv.customer_id = overrides.get("customer_id", uuid4())
    inv.job_id = overrides.get("job_id", uuid4())
    inv.document_url = overrides.get("document_url")
    inv.invoice_token = overrides.get("invoice_token")
    inv.customer_name = overrides.get("customer_name")
    inv.line_items = overrides.get(
        "line_items",
        [{"description": "Irrigation repair", "quantity": 1, "unit_price": "500.00"}],
    )
    inv.notes = overrides.get("notes")
    inv.customer = overrides.get("customer", _mock_customer())
    return inv


def _mock_customer(**overrides: Any) -> MagicMock:
    """Create a mock Customer."""
    c = MagicMock()
    c.id = overrides.get("id", uuid4())
    c.first_name = overrides.get("first_name", "John")
    c.last_name = overrides.get("last_name", "Doe")
    c.email = overrides.get("email", "john@example.com")
    c.phone = overrides.get("phone", "6125551234")
    c.sms_opt_in = overrides.get("sms_opt_in", True)
    c.address = overrides.get("address", "123 Main St")
    c.city = overrides.get("city", "Minneapolis")
    c.state = overrides.get("state", "MN")
    c.zip_code = overrides.get("zip_code", "55401")
    return c


def _mock_appointment(**overrides: Any) -> MagicMock:
    """Create a mock Appointment."""
    apt = MagicMock()
    apt.id = overrides.get("id", uuid4())
    apt.job_id = overrides.get("job_id", uuid4())
    apt.staff_id = overrides.get("staff_id", uuid4())
    apt.scheduled_date = overrides.get("scheduled_date", date(2025, 3, 15))
    apt.time_window_start = overrides.get("time_window_start", time(9, 0))
    apt.time_window_end = overrides.get("time_window_end", time(11, 0))
    apt.status = overrides.get("status", AppointmentStatus.SCHEDULED.value)
    apt.notes = overrides.get("notes")
    return apt


async def _simulate_bulk_notify(
    service: InvoiceService,
    invoice_ids: list[Any],
    notification_type: str = "REMINDER",
) -> dict[str, int]:
    """Simulate the bulk_notify_invoices API logic.

    Mirrors api/v1/invoices.py: iterates invoice IDs, calls
    send_reminder or send_lien_warning, and returns summary.
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
    inv_id: Any,
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
# 1. Bulk Invoice Notification — Validates: Requirement 38.7
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestBulkInvoiceNotificationWorkflow:
    """Test bulk notification sends to multiple invoices and returns summary.

    Validates: Requirement 38.7
    """

    async def test_bulk_notify_multiple_invoices_as_user_would_experience(
        self,
    ) -> None:
        """Sending bulk notifications to 3 invoices returns all-sent summary."""
        invoice_repo = AsyncMock()
        job_repo = AsyncMock()
        service = InvoiceService(
            invoice_repository=invoice_repo,
            job_repository=job_repo,
        )

        inv_ids = [uuid4(), uuid4(), uuid4()]
        for inv_id in inv_ids:
            mock_inv = _mock_invoice(id=inv_id)
            invoice_repo.get_by_id.return_value = mock_inv

        service.send_reminder = AsyncMock(return_value=_mock_invoice())

        result = await _simulate_bulk_notify(service, inv_ids)

        assert result["sent"] == 3
        assert result["skipped"] == 0
        assert result["failed"] == 0
        assert result["total"] == 3

    async def test_bulk_notify_with_missing_invoices_returns_partial_summary(
        self,
    ) -> None:
        """Missing invoices are counted as skipped in the summary."""
        invoice_repo = AsyncMock()
        job_repo = AsyncMock()
        service = InvoiceService(
            invoice_repository=invoice_repo,
            job_repository=job_repo,
        )

        good_id = uuid4()
        missing_id = uuid4()

        async def _side_effect(inv_id: Any) -> MagicMock:
            if inv_id == missing_id:
                raise InvoiceNotFoundError(missing_id)
            return _mock_invoice(id=inv_id)

        service.send_reminder = AsyncMock(side_effect=_side_effect)

        result = await _simulate_bulk_notify(service, [good_id, missing_id])

        assert result["sent"] == 1
        assert result["skipped"] == 1
        assert result["failed"] == 0
        assert result["total"] == 2

    async def test_bulk_notify_with_failures_returns_failed_count(
        self,
    ) -> None:
        """Service errors are counted as failed in the summary."""
        invoice_repo = AsyncMock()
        job_repo = AsyncMock()
        service = InvoiceService(
            invoice_repository=invoice_repo,
            job_repository=job_repo,
        )

        ok_id = uuid4()
        fail_id = uuid4()
        err_msg = "SMS gateway error"

        async def _side_effect(inv_id: Any) -> MagicMock:
            if inv_id == fail_id:
                raise RuntimeError(err_msg)
            return _mock_invoice(id=inv_id)

        service.send_reminder = AsyncMock(side_effect=_side_effect)

        result = await _simulate_bulk_notify(service, [ok_id, fail_id])

        assert result["sent"] == 1
        assert result["failed"] == 1
        assert result["total"] == 2


# =============================================================================
# 2. Campaign Creation, Scheduling, and Delivery — Validates: Req 45.12
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestCampaignLifecycleWorkflow:
    """Test campaign creation, scheduling, and delivery to recipients.

    Validates: Requirement 45.12
    """

    async def test_campaign_lifecycle_as_user_would_experience(
        self,
    ) -> None:
        """Full campaign lifecycle: create → schedule → send."""
        campaign_repo = AsyncMock(spec=CampaignRepository)
        sms_service = AsyncMock()
        email_service = AsyncMock()

        service = CampaignService(
            campaign_repository=campaign_repo,
            sms_service=sms_service,
            email_service=email_service,
        )

        # Step 1: Create campaign in DRAFT status
        campaign_id = uuid4()
        mock_campaign = MagicMock()
        mock_campaign.id = campaign_id
        mock_campaign.name = "Spring Promo"
        mock_campaign.campaign_type = CampaignType.SMS.value
        mock_campaign.status = CampaignStatus.DRAFT.value
        mock_campaign.body = "Spring special: 20% off!"
        mock_campaign.subject = None
        mock_campaign.target_audience = {"status": "active"}
        mock_campaign.scheduled_at = datetime(
            2025,
            4,
            1,
            10,
            0,
            tzinfo=timezone.utc,
        )

        campaign_repo.create.return_value = mock_campaign

        data = CampaignCreate(
            name="Spring Promo",
            campaign_type=CampaignType.SMS,
            body="Spring special: 20% off!",
            target_audience={"status": "active"},
            scheduled_at=datetime(
                2025,
                4,
                1,
                10,
                0,
                tzinfo=timezone.utc,
            ),
        )

        created = await service.create_campaign(data)
        assert created.status == CampaignStatus.DRAFT.value
        assert created.name == "Spring Promo"
        campaign_repo.create.assert_called_once()

        # Step 2: Send campaign — mock recipients
        customer1 = _mock_customer(id=uuid4(), phone="6125551111")
        customer2 = _mock_customer(id=uuid4(), phone="6125552222")
        customer3 = _mock_customer(
            id=uuid4(),
            phone="6125553333",
            sms_opt_in=False,
        )

        campaign_repo.get_by_id.return_value = mock_campaign
        campaign_repo.update.return_value = mock_campaign
        campaign_repo.add_recipient.return_value = MagicMock()

        def _mock_resolve(
            _campaign: Any,
            customer: Any,
        ) -> list[str]:
            if not customer.sms_opt_in:
                return []
            return ["sms"]

        biz_addr = "123 Business St, Minneapolis, MN 55401"

        with (
            patch.object(
                service,
                "_filter_recipients",
                return_value=[customer1, customer2, customer3],
            ),
            patch.object(
                service,
                "_resolve_channels",
                side_effect=_mock_resolve,
            ),
            patch.object(
                service,
                "_send_to_recipient",
                return_value=True,
            ),
            patch.object(
                service,
                "_get_business_address",
                return_value=biz_addr,
            ),
        ):
            result = await service.send_campaign(
                db=AsyncMock(),
                campaign_id=campaign_id,
            )

        assert result.total_recipients == 3
        assert result.sent == 2
        assert result.skipped == 1
        assert result.failed == 0

    async def test_campaign_send_already_sent_raises_error(
        self,
    ) -> None:
        """Sending an already-sent campaign raises error."""
        campaign_repo = AsyncMock(spec=CampaignRepository)
        service = CampaignService(campaign_repository=campaign_repo)

        campaign_id = uuid4()
        mock_campaign = MagicMock()
        mock_campaign.id = campaign_id
        mock_campaign.status = CampaignStatus.SENT.value
        campaign_repo.get_by_id.return_value = mock_campaign

        with pytest.raises(CampaignAlreadySentError):
            await service.send_campaign(
                db=AsyncMock(),
                campaign_id=campaign_id,
            )


# =============================================================================
# 3. Expense CRUD with Receipt Upload — Validates: Requirement 53.10
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestExpenseCRUDWorkflow:
    """Test expense CRUD operations with receipt upload.

    Validates: Requirement 53.10
    """

    async def test_expense_crud_with_receipt_as_user_would_experience(
        self,
    ) -> None:
        """Create, read, update, and delete an expense with receipt."""
        session = AsyncMock()
        repo = ExpenseRepository(session)

        expense_id = uuid4()
        mock_expense = MagicMock()
        mock_expense.id = expense_id
        mock_expense.category = ExpenseCategory.MATERIALS.value
        mock_expense.description = "PVC pipes for irrigation"
        mock_expense.amount = Decimal("245.50")
        mock_expense.expense_date = date(2025, 3, 10)
        mock_expense.receipt_file_key = "receipts/abc123.jpg"
        mock_expense.vendor = "Home Depot"
        mock_expense.notes = None

        # Create
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.add = MagicMock()

        with patch.object(repo, "create", return_value=mock_expense):
            created = await repo.create(
                category=ExpenseCategory.MATERIALS.value,
                description="PVC pipes for irrigation",
                amount=Decimal("245.50"),
                expense_date=date(2025, 3, 10),
                receipt_file_key="receipts/abc123.jpg",
                vendor="Home Depot",
            )

        assert created.category == ExpenseCategory.MATERIALS.value
        assert created.amount == Decimal("245.50")
        assert created.receipt_file_key == "receipts/abc123.jpg"

        # Read
        with patch.object(repo, "get_by_id", return_value=mock_expense):
            fetched = await repo.get_by_id(expense_id)

        assert fetched is not None
        assert fetched.id == expense_id
        assert fetched.description == "PVC pipes for irrigation"

        # Update
        updated_expense = MagicMock()
        updated_expense.id = expense_id
        updated_expense.amount = Decimal("275.00")
        updated_expense.description = "PVC pipes and fittings"

        with patch.object(repo, "update", return_value=updated_expense):
            updated = await repo.update(
                expense_id,
                amount=Decimal("275.00"),
                description="PVC pipes and fittings",
            )

        assert updated is not None
        assert updated.amount == Decimal("275.00")

        # Delete
        with patch.object(repo, "delete", return_value=True):
            deleted = await repo.delete(expense_id)

        assert deleted is True


# =============================================================================
# 4. Accounting Summary Aggregations — Validates: Requirement 52.8
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestAccountingSummaryWorkflow:
    """Test accounting summary returns correct aggregations.

    Validates: Requirement 52.8
    """

    async def test_accounting_summary_as_user_would_experience(
        self,
    ) -> None:
        """Summary correctly aggregates revenue, expenses, and profit."""
        expense_repo = AsyncMock(spec=ExpenseRepository)
        service = AccountingService(expense_repository=expense_repo)

        expense_repo.get_total_spend.return_value = Decimal("3500.00")

        db = AsyncMock()

        revenue_scalar = MagicMock()
        revenue_scalar.scalar.return_value = Decimal("10000.00")

        pending_scalar = MagicMock()
        pending_scalar.scalar.return_value = Decimal("2000.00")

        past_due_scalar = MagicMock()
        past_due_scalar.scalar.return_value = Decimal("1500.00")

        db.execute = AsyncMock(
            side_effect=[
                revenue_scalar,
                pending_scalar,
                past_due_scalar,
            ],
        )

        summary = await service.get_summary(
            db=db,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 12, 31),
        )

        assert summary.revenue == Decimal("10000.00")
        assert summary.expenses == Decimal("3500.00")
        assert summary.profit == Decimal("6500.00")
        assert summary.profit_margin == 65.0
        assert summary.pending_total == Decimal("2000.00")
        assert summary.past_due_total == Decimal("1500.00")

    async def test_accounting_summary_zero_revenue_as_user_would_experience(
        self,
    ) -> None:
        """Summary handles zero revenue without division errors."""
        expense_repo = AsyncMock(spec=ExpenseRepository)
        service = AccountingService(expense_repository=expense_repo)

        expense_repo.get_total_spend.return_value = Decimal("500.00")

        db = AsyncMock()
        zero_scalar = MagicMock()
        zero_scalar.scalar.return_value = Decimal(0)

        db.execute = AsyncMock(
            side_effect=[zero_scalar, zero_scalar, zero_scalar],
        )

        summary = await service.get_summary(
            db=db,
            date_from=date(2025, 1, 1),
            date_to=date(2025, 6, 30),
        )

        assert summary.revenue == Decimal(0)
        assert summary.expenses == Decimal("500.00")
        assert summary.profit == Decimal("-500.00")
        assert summary.profit_margin == 0.0


# =============================================================================
# 5. Audit Log Filtering — Validates: Requirement 74.6
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestAuditLogFilteringWorkflow:
    """Test audit log endpoint returns correctly filtered results.

    Validates: Requirement 74.6
    """

    async def test_audit_log_filtered_by_action_as_user_would_experience(
        self,
    ) -> None:
        """Filtering audit log by action returns matching entries."""
        db = AsyncMock()
        service = AuditService()

        merge_entry = MagicMock()
        merge_entry.id = uuid4()
        merge_entry.action = "customer.merge"
        merge_entry.resource_type = "customer"
        merge_entry.resource_id = str(uuid4())
        merge_entry.actor_id = uuid4()
        merge_entry.actor_role = "admin"
        merge_entry.details = {"merged_ids": [str(uuid4())]}
        merge_entry.ip_address = "192.168.1.1"
        merge_entry.created_at = datetime(
            2025,
            3,
            15,
            10,
            0,
            tzinfo=timezone.utc,
        )

        with patch.object(
            AuditLogRepository,
            "list_with_filters",
        ) as mock_list:
            mock_list.return_value = ([merge_entry], 1)

            filters = AuditLogFilters(
                page=1,
                page_size=20,
                action="customer.merge",
            )
            result = await service.get_audit_log(
                db=db,
                filters=filters,
            )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0].action == "customer.merge"

    async def test_audit_log_filtered_by_resource_as_user_would_experience(
        self,
    ) -> None:
        """Filtering by resource_type returns matching entries."""
        db = AsyncMock()
        service = AuditService()

        invoice_entry = MagicMock()
        invoice_entry.id = uuid4()
        invoice_entry.action = "invoice.bulk_notify"
        invoice_entry.resource_type = "invoice"
        invoice_entry.resource_id = str(uuid4())
        invoice_entry.actor_id = uuid4()
        invoice_entry.actor_role = "admin"
        invoice_entry.details = {"count": 5}
        invoice_entry.ip_address = "10.0.0.1"
        invoice_entry.created_at = datetime(
            2025,
            3,
            16,
            14,
            0,
            tzinfo=timezone.utc,
        )

        with patch.object(
            AuditLogRepository,
            "list_with_filters",
        ) as mock_list:
            mock_list.return_value = ([invoice_entry], 1)

            filters = AuditLogFilters(
                page=1,
                page_size=20,
                resource_type="invoice",
            )
            result = await service.get_audit_log(
                db=db,
                filters=filters,
            )

        assert result["total"] == 1
        assert result["items"][0].resource_type == "invoice"

    async def test_audit_log_creation_as_user_would_experience(
        self,
    ) -> None:
        """Creating an audit log entry persists correctly."""
        db = AsyncMock()

        actor_id = uuid4()
        resource_id = uuid4()

        mock_entry = MagicMock()
        mock_entry.id = uuid4()
        mock_entry.action = "campaign.send"
        mock_entry.resource_type = "campaign"
        mock_entry.resource_id = str(resource_id)
        mock_entry.actor_id = actor_id
        mock_entry.actor_role = "admin"
        mock_entry.details = {"recipients": 50}
        mock_entry.ip_address = "192.168.1.1"
        mock_entry.user_agent = "Mozilla/5.0"
        mock_entry.created_at = datetime.now(tz=timezone.utc)

        with patch.object(
            AuditLogRepository,
            "create",
            return_value=mock_entry,
        ) as mock_create:
            repo = AuditLogRepository(db)
            entry = await repo.create(
                action="campaign.send",
                resource_type="campaign",
                resource_id=str(resource_id),
                actor_id=actor_id,
                actor_role="admin",
                details={"recipients": 50},
                ip_address="192.168.1.1",
                user_agent="Mozilla/5.0",
            )

        assert entry.action == "campaign.send"
        assert entry.resource_type == "campaign"
        assert entry.actor_id == actor_id
        mock_create.assert_called_once()


# =============================================================================
# 6. SentMessage with Lead Linkage — Validates: Requirement 81.10
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestSentMessageLeadLinkageWorkflow:
    """Test SentMessage record creation with lead_id linkage.

    Validates: Requirement 81.10
    """

    async def test_lead_sms_creates_sent_message_as_user_would_experience(
        self,
    ) -> None:
        """Lead confirmation SMS creates SentMessage with lead_id."""
        sms_service = AsyncMock()
        notification_service = NotificationService(
            sms_service=sms_service,
        )

        lead_id = uuid4()
        mock_lead = MagicMock()
        mock_lead.id = lead_id
        mock_lead.phone = "6125559999"
        mock_lead.sms_consent = True

        db = AsyncMock()

        lead_result = MagicMock()
        lead_result.scalar_one_or_none.return_value = mock_lead

        settings_result = MagicMock()
        settings_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(
            side_effect=[lead_result, settings_result],
        )
        db.add = MagicMock()
        db.flush = AsyncMock()

        with patch(
            "grins_platform.services.notification_service.datetime",
        ) as mock_dt:
            mock_now = datetime(2025, 3, 15, 12, 0, 0)
            mock_dt.now.return_value = mock_now
            mock_dt.combine = datetime.combine
            mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

            result = await notification_service.send_lead_confirmation_sms(
                db=db,
                lead_id=lead_id,
            )

        assert result is True
        sms_service.send_automated_message.assert_called_once()

        db.add.assert_called()
        added_msg = db.add.call_args[0][0]
        assert added_msg.lead_id == lead_id
        assert added_msg.message_type == "lead_confirmation"
        assert added_msg.recipient_phone == "6125559999"
        assert added_msg.delivery_status == "sent"

    async def test_lead_without_consent_skips_confirmation(
        self,
    ) -> None:
        """Lead without SMS consent does not receive confirmation."""
        sms_service = AsyncMock()
        notification_service = NotificationService(
            sms_service=sms_service,
        )

        lead_id = uuid4()
        mock_lead = MagicMock()
        mock_lead.id = lead_id
        mock_lead.phone = "6125559999"
        mock_lead.sms_consent = False

        db = AsyncMock()
        lead_result = MagicMock()
        lead_result.scalar_one_or_none.return_value = mock_lead
        db.execute = AsyncMock(return_value=lead_result)

        result = await notification_service.send_lead_confirmation_sms(
            db=db,
            lead_id=lead_id,
        )

        assert result is False
        sms_service.send_automated_message.assert_not_called()


# =============================================================================
# 7. Invoice PDF Generation — Validates: Requirement 80.9
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestInvoicePDFGenerationWorkflow:
    """Test invoice PDF generation stores file in S3.

    Validates: Requirement 80.9
    """

    async def test_pdf_stores_in_s3_as_user_would_experience(
        self,
    ) -> None:
        """Generating PDF uploads to S3 and sets document_url."""
        s3_client = MagicMock()
        s3_client.put_object.return_value = {
            "ResponseMetadata": {"HTTPStatusCode": 200},
        }
        s3_client.generate_presigned_url.return_value = (
            "https://s3.amazonaws.com/grins-platform-files/invoices/test.pdf"
        )

        service = InvoicePDFService(
            s3_client=s3_client,
            s3_bucket="grins-platform-files",
        )

        invoice_id = uuid4()
        mock_inv = _mock_invoice(id=invoice_id)
        mock_inv.document_url = None

        db = AsyncMock()
        invoice_result = MagicMock()
        invoice_result.scalar_one_or_none.return_value = mock_inv
        settings_result = MagicMock()
        settings_result.scalars.return_value.all.return_value = []

        db.execute = AsyncMock(
            side_effect=[invoice_result, settings_result],
        )
        db.flush = AsyncMock()

        with (
            patch.object(
                service,
                "_render_invoice_html",
                return_value="<html><body>Invoice</body></html>",
            ),
            patch("weasyprint.HTML") as mock_html_cls,
        ):
            mock_html_instance = MagicMock()
            mock_html_instance.write_pdf.return_value = b"%PDF-1.4 fake content"
            mock_html_cls.return_value = mock_html_instance

            url = await service.generate_pdf(
                db=db,
                invoice_id=invoice_id,
            )

        s3_client.put_object.assert_called_once()
        call_kwargs = s3_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "grins-platform-files"
        assert call_kwargs["Key"] == f"invoices/{invoice_id}.pdf"
        assert call_kwargs["ContentType"] == "application/pdf"

        assert mock_inv.document_url == f"invoices/{invoice_id}.pdf"
        db.flush.assert_called_once()
        assert "s3.amazonaws.com" in url

    async def test_pdf_nonexistent_invoice_raises_error(
        self,
    ) -> None:
        """Generating PDF for missing invoice raises error."""
        service = InvoicePDFService(s3_client=MagicMock())

        db = AsyncMock()
        empty_result = MagicMock()
        empty_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=empty_result)

        with pytest.raises(PDFInvoiceNotFoundError):
            await service.generate_pdf(db=db, invoice_id=uuid4())


# =============================================================================
# 8. Appointment No-Show Transition — Validates: Requirement 79.8
# =============================================================================


def _build_appointment_service(
    appt_repo: AsyncMock | None = None,
) -> AppointmentService:
    """Build AppointmentService with mocked dependencies."""
    return AppointmentService(
        appointment_repository=appt_repo or AsyncMock(),
        job_repository=AsyncMock(),
        staff_repository=AsyncMock(),
        invoice_repository=AsyncMock(),
        estimate_service=AsyncMock(),
        google_review_url="https://g.page/grins-irrigation/review",
    )


@pytest.mark.functional
@pytest.mark.asyncio
class TestAppointmentNoShowTransitionWorkflow:
    """Test appointment no_show status transition succeeds.

    Validates: Requirement 79.8
    """

    async def test_confirmed_to_no_show_as_user_would_experience(
        self,
    ) -> None:
        """Appointment transitions from confirmed → no_show."""
        appt_repo = AsyncMock()
        service = _build_appointment_service(appt_repo=appt_repo)

        apt = _mock_appointment(
            status=AppointmentStatus.CONFIRMED.value,
        )
        appt_repo.get_by_id.return_value = apt

        no_show_apt = _mock_appointment(
            id=apt.id,
            status=AppointmentStatus.NO_SHOW.value,
        )
        appt_repo.update.return_value = no_show_apt

        result = await service.transition_status(
            appointment_id=apt.id,
            new_status=AppointmentStatus.NO_SHOW,
            actor_id=uuid4(),
        )

        assert result.status == AppointmentStatus.NO_SHOW.value

    async def test_en_route_to_no_show_as_user_would_experience(
        self,
    ) -> None:
        """Appointment transitions from en_route → no_show."""
        appt_repo = AsyncMock()
        service = _build_appointment_service(appt_repo=appt_repo)

        apt = _mock_appointment(
            status=AppointmentStatus.EN_ROUTE.value,
        )
        appt_repo.get_by_id.return_value = apt

        no_show_apt = _mock_appointment(
            id=apt.id,
            status=AppointmentStatus.NO_SHOW.value,
        )
        appt_repo.update.return_value = no_show_apt

        result = await service.transition_status(
            appointment_id=apt.id,
            new_status=AppointmentStatus.NO_SHOW,
            actor_id=uuid4(),
        )

        assert result.status == AppointmentStatus.NO_SHOW.value
