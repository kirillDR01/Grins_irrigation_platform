"""Integration test fixtures for Phase 8 features.

This module provides fixtures for integration testing of:
- Authentication (login, tokens, RBAC)
- Schedule Clear (audit records)
- Invoice Management (invoices, payments, liens)

Requirements: 29.1 - Create test fixtures
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from grins_platform.main import app
from grins_platform.models.enums import (
    InvoiceStatus,
    JobStatus,
    PaymentMethod,
    StaffRole,
    UserRole,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


# =============================================================================
# Authentication Fixtures
# =============================================================================


@pytest.fixture
def sample_staff_id() -> uuid.UUID:
    """Generate a sample staff UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_admin_staff(sample_staff_id: uuid.UUID) -> MagicMock:
    """Create a mock admin staff member with authentication enabled."""
    staff = MagicMock()
    staff.id = sample_staff_id
    staff.name = "Admin User"
    staff.phone = "6125550001"
    staff.email = "admin@grins.com"
    staff.role = StaffRole.ADMIN.value
    staff.username = "admin"
    staff.password_hash = "$2b$12$test_hash"  # Mock bcrypt hash
    staff.is_login_enabled = True
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def sample_manager_staff() -> MagicMock:
    """Create a mock manager staff member with authentication enabled."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Manager User"
    staff.phone = "6125550002"
    staff.email = "manager@grins.com"
    staff.role = UserRole.MANAGER.value
    staff.username = "manager"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def sample_tech_staff() -> MagicMock:
    """Create a mock tech staff member with authentication enabled."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Tech User"
    staff.phone = "6125550003"
    staff.email = "tech@grins.com"
    staff.role = StaffRole.TECH.value
    staff.username = "tech"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def sample_locked_staff() -> MagicMock:
    """Create a mock staff member with locked account."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Locked User"
    staff.phone = "6125550004"
    staff.email = "locked@grins.com"
    staff.role = StaffRole.TECH.value
    staff.username = "locked"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = True
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 5
    staff.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def sample_disabled_staff() -> MagicMock:
    """Create a mock staff member with login disabled."""
    staff = MagicMock()
    staff.id = uuid.uuid4()
    staff.name = "Disabled User"
    staff.phone = "6125550005"
    staff.email = "disabled@grins.com"
    staff.role = StaffRole.TECH.value
    staff.username = "disabled"
    staff.password_hash = "$2b$12$test_hash"
    staff.is_login_enabled = False
    staff.is_active = True
    staff.last_login = None
    staff.failed_login_attempts = 0
    staff.locked_until = None
    staff.created_at = datetime.now(timezone.utc)
    staff.updated_at = datetime.now(timezone.utc)
    return staff


@pytest.fixture
def valid_access_token() -> str:
    """Return a mock valid access token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_access_token"


@pytest.fixture
def valid_refresh_token() -> str:
    """Return a mock valid refresh token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_refresh_token"


@pytest.fixture
def expired_access_token() -> str:
    """Return a mock expired access token for testing."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired_token"


# =============================================================================
# Schedule Clear Audit Fixtures
# =============================================================================


@pytest.fixture
def sample_schedule_clear_audit_id() -> uuid.UUID:
    """Generate a sample schedule clear audit UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_appointments_data() -> list[dict[str, Any]]:
    """Create sample appointments data for audit records."""
    return [
        {
            "id": str(uuid.uuid4()),
            "job_id": str(uuid.uuid4()),
            "staff_id": str(uuid.uuid4()),
            "scheduled_date": "2025-01-29",
            "time_window_start": "09:00",
            "time_window_end": "11:00",
            "status": "scheduled",
            "customer_name": "John Doe",
            "address": "123 Main St, Eden Prairie, MN",
        },
        {
            "id": str(uuid.uuid4()),
            "job_id": str(uuid.uuid4()),
            "staff_id": str(uuid.uuid4()),
            "scheduled_date": "2025-01-29",
            "time_window_start": "11:00",
            "time_window_end": "13:00",
            "status": "scheduled",
            "customer_name": "Jane Smith",
            "address": "456 Oak Ave, Plymouth, MN",
        },
    ]


@pytest.fixture
def sample_jobs_reset() -> list[uuid.UUID]:
    """Create sample job IDs that were reset."""
    return [uuid.uuid4(), uuid.uuid4()]


@pytest.fixture
def sample_schedule_clear_audit(
    sample_schedule_clear_audit_id: uuid.UUID,
    sample_staff_id: uuid.UUID,
    sample_appointments_data: list[dict[str, Any]],
    sample_jobs_reset: list[uuid.UUID],
) -> MagicMock:
    """Create a mock ScheduleClearAudit record."""
    audit = MagicMock()
    audit.id = sample_schedule_clear_audit_id
    audit.schedule_date = date(2025, 1, 29)
    audit.appointments_data = sample_appointments_data
    audit.jobs_reset = sample_jobs_reset
    audit.appointment_count = len(sample_appointments_data)
    audit.cleared_by = sample_staff_id
    audit.cleared_at = datetime.now(timezone.utc)
    audit.notes = "Test clear operation"
    audit.created_at = datetime.now(timezone.utc)
    return audit


@pytest.fixture
def sample_recent_clear_audits(
    sample_staff_id: uuid.UUID,
) -> list[MagicMock]:
    """Create a list of recent schedule clear audit records."""
    audits = []
    for i in range(3):
        audit = MagicMock()
        audit.id = uuid.uuid4()
        audit.schedule_date = date(2025, 1, 29) - timedelta(days=i)
        audit.appointments_data = [
            {"id": str(uuid.uuid4()), "customer_name": f"Customer {i}"},
        ]
        audit.jobs_reset = [uuid.uuid4()]
        audit.appointment_count = 1
        audit.cleared_by = sample_staff_id
        audit.cleared_at = datetime.now(timezone.utc) - timedelta(hours=i * 2)
        audit.notes = f"Clear operation {i}"
        audit.created_at = datetime.now(timezone.utc) - timedelta(hours=i * 2)
        audits.append(audit)
    return audits


# =============================================================================
# Invoice Fixtures
# =============================================================================


@pytest.fixture
def sample_invoice_id() -> uuid.UUID:
    """Generate a sample invoice UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_job_id() -> uuid.UUID:
    """Generate a sample job UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_customer_id() -> uuid.UUID:
    """Generate a sample customer UUID."""
    return uuid.uuid4()


@pytest.fixture
def sample_line_items() -> list[dict[str, Any]]:
    """Create sample invoice line items."""
    return [
        {
            "description": "Spring Startup - 6 zones",
            "quantity": 1,
            "unit_price": "150.00",
            "total": "150.00",
        },
        {
            "description": "Broken head replacement",
            "quantity": 2,
            "unit_price": "50.00",
            "total": "100.00",
        },
    ]


@pytest.fixture
def sample_draft_invoice(
    sample_invoice_id: uuid.UUID,
    sample_job_id: uuid.UUID,
    sample_customer_id: uuid.UUID,
    sample_line_items: list[dict[str, Any]],
) -> MagicMock:
    """Create a mock draft invoice."""
    invoice = MagicMock()
    invoice.id = sample_invoice_id
    invoice.job_id = sample_job_id
    invoice.customer_id = sample_customer_id
    invoice.invoice_number = "INV-2025-0001"
    invoice.amount = Decimal("250.00")
    invoice.late_fee_amount = Decimal("0.00")
    invoice.total_amount = Decimal("250.00")
    invoice.invoice_date = date.today()
    invoice.due_date = date.today() + timedelta(days=30)
    invoice.status = InvoiceStatus.DRAFT.value
    invoice.payment_method = None
    invoice.payment_reference = None
    invoice.paid_at = None
    invoice.paid_amount = Decimal("0.00")
    invoice.reminder_count = 0
    invoice.last_reminder_sent = None
    invoice.lien_eligible = False
    invoice.lien_warning_sent = None
    invoice.lien_filed_date = None
    invoice.line_items = sample_line_items
    invoice.notes = "Test invoice"
    invoice.created_at = datetime.now(timezone.utc)
    invoice.updated_at = datetime.now(timezone.utc)
    return invoice


@pytest.fixture
def sample_sent_invoice(sample_draft_invoice: MagicMock) -> MagicMock:
    """Create a mock sent invoice."""
    invoice = sample_draft_invoice
    invoice.status = InvoiceStatus.SENT.value
    return invoice


@pytest.fixture
def sample_paid_invoice(sample_draft_invoice: MagicMock) -> MagicMock:
    """Create a mock fully paid invoice."""
    invoice = sample_draft_invoice
    invoice.status = InvoiceStatus.PAID.value
    invoice.payment_method = PaymentMethod.VENMO.value
    invoice.payment_reference = "venmo-123456"
    invoice.paid_at = datetime.now(timezone.utc)
    invoice.paid_amount = Decimal("250.00")
    return invoice


@pytest.fixture
def sample_partial_invoice(sample_draft_invoice: MagicMock) -> MagicMock:
    """Create a mock partially paid invoice."""
    invoice = sample_draft_invoice
    invoice.status = InvoiceStatus.PARTIAL.value
    invoice.payment_method = PaymentMethod.CHECK.value
    invoice.payment_reference = "Check #1234"
    invoice.paid_at = datetime.now(timezone.utc)
    invoice.paid_amount = Decimal("100.00")
    return invoice


@pytest.fixture
def sample_overdue_invoice(sample_draft_invoice: MagicMock) -> MagicMock:
    """Create a mock overdue invoice."""
    invoice = sample_draft_invoice
    invoice.status = InvoiceStatus.OVERDUE.value
    invoice.due_date = date.today() - timedelta(days=7)
    invoice.reminder_count = 2
    invoice.last_reminder_sent = datetime.now(timezone.utc) - timedelta(days=3)
    return invoice


@pytest.fixture
def sample_lien_eligible_invoice(
    sample_job_id: uuid.UUID,
    sample_customer_id: uuid.UUID,
) -> MagicMock:
    """Create a mock lien-eligible invoice (installation job)."""
    invoice = MagicMock()
    invoice.id = uuid.uuid4()
    invoice.job_id = sample_job_id
    invoice.customer_id = sample_customer_id
    invoice.invoice_number = "INV-2025-0002"
    invoice.amount = Decimal("5000.00")
    invoice.late_fee_amount = Decimal("0.00")
    invoice.total_amount = Decimal("5000.00")
    invoice.invoice_date = date.today() - timedelta(days=50)
    invoice.due_date = date.today() - timedelta(days=20)
    invoice.status = InvoiceStatus.OVERDUE.value
    invoice.payment_method = None
    invoice.payment_reference = None
    invoice.paid_at = None
    invoice.paid_amount = Decimal("0.00")
    invoice.reminder_count = 3
    invoice.last_reminder_sent = datetime.now(timezone.utc) - timedelta(days=5)
    invoice.lien_eligible = True
    invoice.lien_warning_sent = None
    invoice.lien_filed_date = None
    invoice.line_items = [
        {"description": "New irrigation system - 8 zones", "quantity": 1,
         "unit_price": "5000.00", "total": "5000.00"},
    ]
    invoice.notes = "Installation job - lien eligible"
    invoice.created_at = datetime.now(timezone.utc) - timedelta(days=50)
    invoice.updated_at = datetime.now(timezone.utc)
    return invoice


@pytest.fixture
def sample_lien_warning_invoice(
    sample_lien_eligible_invoice: MagicMock,
) -> MagicMock:
    """Create a mock invoice with lien warning sent."""
    invoice = sample_lien_eligible_invoice
    invoice.status = InvoiceStatus.LIEN_WARNING.value
    invoice.lien_warning_sent = datetime.now(timezone.utc) - timedelta(days=10)
    return invoice


@pytest.fixture
def sample_lien_filed_invoice(
    sample_lien_warning_invoice: MagicMock,
) -> MagicMock:
    """Create a mock invoice with lien filed."""
    invoice = sample_lien_warning_invoice
    invoice.status = InvoiceStatus.LIEN_FILED.value
    invoice.lien_filed_date = date.today() - timedelta(days=5)
    return invoice


@pytest.fixture
def sample_invoices_list(
    sample_customer_id: uuid.UUID,
) -> list[MagicMock]:
    """Create a list of sample invoices with various statuses."""
    invoices = []
    statuses = [
        InvoiceStatus.DRAFT,
        InvoiceStatus.SENT,
        InvoiceStatus.PAID,
        InvoiceStatus.OVERDUE,
        InvoiceStatus.PARTIAL,
    ]
    for i, status in enumerate(statuses):
        invoice = MagicMock()
        invoice.id = uuid.uuid4()
        invoice.job_id = uuid.uuid4()
        invoice.customer_id = sample_customer_id
        invoice.invoice_number = f"INV-2025-{i + 1:04d}"
        invoice.amount = Decimal(f"{(i + 1) * 100}.00")
        invoice.late_fee_amount = Decimal("0.00")
        invoice.total_amount = Decimal(f"{(i + 1) * 100}.00")
        invoice.invoice_date = date.today() - timedelta(days=i * 5)
        invoice.due_date = date.today() + timedelta(days=30 - i * 10)
        invoice.status = status.value
        invoice.payment_method = None
        invoice.payment_reference = None
        invoice.paid_at = None
        invoice.paid_amount = Decimal("0.00")
        invoice.reminder_count = 0
        invoice.last_reminder_sent = None
        invoice.lien_eligible = False
        invoice.lien_warning_sent = None
        invoice.lien_filed_date = None
        invoice.line_items = []
        invoice.notes = f"Invoice {i + 1}"
        invoice.created_at = datetime.now(timezone.utc) - timedelta(days=i * 5)
        invoice.updated_at = datetime.now(timezone.utc)
        invoices.append(invoice)
    return invoices


# =============================================================================
# Job Fixtures for Invoice Generation
# =============================================================================


@pytest.fixture
def sample_completed_job(
    sample_job_id: uuid.UUID,
    sample_customer_id: uuid.UUID,
) -> MagicMock:
    """Create a mock completed job for invoice generation."""
    job = MagicMock()
    job.id = sample_job_id
    job.customer_id = sample_customer_id
    job.property_id = uuid.uuid4()
    job.job_type = "spring_startup"
    job.status = JobStatus.COMPLETED.value
    job.quoted_amount = Decimal("150.00")
    job.final_amount = Decimal("175.00")  # Additional work done
    job.payment_collected_on_site = False
    job.is_deleted = False
    job.description = "Spring startup service"
    job.created_at = datetime.now(timezone.utc) - timedelta(days=1)
    job.updated_at = datetime.now(timezone.utc)
    return job


@pytest.fixture
def sample_job_payment_collected(
    sample_completed_job: MagicMock,
) -> MagicMock:
    """Create a mock job where payment was collected on site."""
    job = sample_completed_job
    job.payment_collected_on_site = True
    return job


@pytest.fixture
def sample_installation_job(
    sample_customer_id: uuid.UUID,
) -> MagicMock:
    """Create a mock installation job (lien-eligible)."""
    job = MagicMock()
    job.id = uuid.uuid4()
    job.customer_id = sample_customer_id
    job.property_id = uuid.uuid4()
    job.job_type = "installation"
    job.status = JobStatus.COMPLETED.value
    job.quoted_amount = Decimal("5000.00")
    job.final_amount = Decimal("5500.00")
    job.payment_collected_on_site = False
    job.is_deleted = False
    job.description = "New irrigation system installation"
    job.created_at = datetime.now(timezone.utc) - timedelta(days=7)
    job.updated_at = datetime.now(timezone.utc)
    return job


# =============================================================================
# HTTP Client Fixtures with Authentication
# =============================================================================


@pytest_asyncio.fixture
async def auth_client_admin() -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated async HTTP client with admin role."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Add mock admin authentication
        ac.headers.update({
            "Authorization": "Bearer admin-test-token",
            "X-CSRF-Token": "test-csrf-token",
        })
        yield ac


@pytest_asyncio.fixture
async def auth_client_manager() -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated async HTTP client with manager role."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Add mock manager authentication
        ac.headers.update({
            "Authorization": "Bearer manager-test-token",
            "X-CSRF-Token": "test-csrf-token",
        })
        yield ac


@pytest_asyncio.fixture
async def auth_client_tech() -> AsyncGenerator[AsyncClient, None]:
    """Create an authenticated async HTTP client with tech role."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Add mock tech authentication
        ac.headers.update({
            "Authorization": "Bearer tech-test-token",
            "X-CSRF-Token": "test-csrf-token",
        })
        yield ac


@pytest_asyncio.fixture
async def unauthenticated_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an unauthenticated async HTTP client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
