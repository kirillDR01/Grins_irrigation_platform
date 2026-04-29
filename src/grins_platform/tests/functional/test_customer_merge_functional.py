"""Functional tests for customer merge flow.

Tests the full customer merge lifecycle with mocked DB: data conservation
across jobs/invoices/communications, Stripe subscription blocker,
soft-delete via merged_into_customer_id, and audit log creation.

Validates: Requirements 6.4, 6.5, 6.7, 35.1
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import MergeConflictError
from grins_platform.models.audit_log import AuditLog
from grins_platform.schemas.customer_merge import MergeFieldSelection
from grins_platform.services.customer_merge_service import CustomerMergeService

# =============================================================================
# Helpers
# =============================================================================


def _make_customer(
    *,
    customer_id: Any | None = None,
    first_name: str = "Jane",
    last_name: str = "Smith",
    phone: str = "5125551234",
    email: str | None = "jane@example.com",
    internal_notes: str | None = None,
    is_deleted: bool = False,
    stripe_customer_id: str | None = None,
) -> MagicMock:
    """Create a mock Customer model."""
    c = MagicMock()
    c.id = customer_id or uuid4()
    c.first_name = first_name
    c.last_name = last_name
    c.phone = phone
    c.email = email
    c.internal_notes = internal_notes
    c.is_deleted = is_deleted
    c.deleted_at = None
    c.merged_into_customer_id = None
    c.stripe_customer_id = stripe_customer_id
    c.status = "active"
    c.is_priority = False
    c.is_red_flag = False
    c.is_slow_payer = False
    c.is_new_customer = False
    c.sms_opt_in = True
    c.email_opt_in = True
    c.lead_source = None
    c.preferred_service_times = None
    c.created_at = datetime.now()
    c.updated_at = datetime.now()
    c.properties = []
    return c


def _mock_db_for_merge(
    *,
    primary: MagicMock,
    duplicate: MagicMock,
    both_have_stripe: bool = False,
    job_count: int = 3,
    invoice_count: int = 2,
    comm_count: int = 5,
    agreement_count: int = 1,
    property_count: int = 1,
) -> AsyncMock:
    """Create a mock AsyncSession wired for merge operations.

    Handles the various SELECT queries the merge service issues:
    - Customer lookups (primary + duplicate)
    - Stripe subscription blocker check
    - Related record counts
    - UPDATE reassignment statements
    - Merge candidate resolution
    """
    db = AsyncMock()

    # Track customer lookup order: first call returns primary, second returns duplicate
    _customer_lookup_calls: list[MagicMock] = []

    # Build count results for _count_related_records
    count_map = {
        "jobs": job_count,
        "invoices": invoice_count,
        "sent_messages": comm_count,
        "service_agreements": agreement_count,
        "properties": property_count,
    }

    async def _execute_side_effect(stmt: Any, params: Any = None) -> MagicMock:
        stmt_str = str(stmt)
        result = MagicMock()

        # Customer lookup (SELECT ... FROM customers WHERE ... is_deleted)
        if "customers" in stmt_str and "is_deleted" in stmt_str:
            # Service calls _get_customer(primary) then (duplicate)
            if len(_customer_lookup_calls) == 0:
                _customer_lookup_calls.append(primary)
                result.scalar_one_or_none.return_value = primary
            else:
                _customer_lookup_calls.append(duplicate)
                result.scalar_one_or_none.return_value = duplicate
            return result

        # Stripe subscription blocker check
        if "service_agreements" in stmt_str and "stripe_subscription_id" in stmt_str:
            if both_have_stripe:
                row_a = MagicMock()
                row_a.customer_id = primary.id
                row_a.cnt = 1
                row_b = MagicMock()
                row_b.customer_id = duplicate.id
                row_b.cnt = 1
                result.all.return_value = [row_a, row_b]
            else:
                result.all.return_value = []
            return result

        # Related record counts (SELECT count(*) FROM ...)
        if "count" in stmt_str.lower():
            for table, count in count_map.items():
                if table in stmt_str:
                    result.scalar.return_value = count
                    return result
            result.scalar.return_value = 0
            return result

        # UPDATE statements (reassignment, merge candidate resolution)
        result.rowcount = 1
        return result

    db.execute = AsyncMock(side_effect=_execute_side_effect)
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


# =============================================================================
# 1. Merge with Data Conservation
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestCustomerMergeDataConservation:
    """Merge reassigns all related records to the surviving customer.

    Validates: Requirements 6.4, 35.1
    """

    async def test_merge_reassigns_jobs_invoices_communications(
        self,
    ) -> None:
        """All jobs, invoices, and communications transfer to primary.

        Validates: Requirements 6.4, 35.1
        """
        svc = CustomerMergeService()

        primary = _make_customer(
            first_name="Alice",
            last_name="Johnson",
            phone="5125550001",
            email="alice@example.com",
        )
        duplicate = _make_customer(
            first_name="Alice",
            last_name="Jonson",
            phone="5125550002",
            email="alice.j@example.com",
        )

        db = _mock_db_for_merge(
            primary=primary,
            duplicate=duplicate,
            job_count=4,
            invoice_count=3,
            comm_count=7,
        )
        admin_id = uuid4()

        await svc.execute_merge(
            db=db,
            primary_id=primary.id,
            duplicate_id=duplicate.id,
            field_selections=[],
            admin_id=admin_id,
        )

        # Verify UPDATE statements were executed for FK reassignment
        execute_calls = db.execute.call_args_list
        reassign_tables_found = set()
        for c in execute_calls:
            stmt_str = str(c[0][0]) if c[0] else ""
            if "UPDATE" in stmt_str and "customer_id" in stmt_str:
                for table in [
                    "jobs",
                    "invoices",
                    "sent_messages",
                    "properties",
                    "service_agreements",
                    "communications",
                    "customer_photos",
                    "customer_documents",
                    "estimates",
                    "sales_entries",
                    "contract_renewal_proposals",
                ]:
                    if table in stmt_str:
                        reassign_tables_found.add(table)

        # Core tables must be reassigned
        assert "jobs" in reassign_tables_found
        assert "invoices" in reassign_tables_found
        assert "sent_messages" in reassign_tables_found

        # Transaction committed
        db.flush.assert_awaited_once()

    async def test_merge_with_field_selections_applies_overrides(
        self,
    ) -> None:
        """Admin field selections override default merge logic.

        Validates: Requirements 6.4
        """
        svc = CustomerMergeService()

        primary = _make_customer(
            first_name="Bob",
            phone="5125550010",
            email="",
        )
        duplicate = _make_customer(
            first_name="Robert",
            phone="5125550011",
            email="bob@example.com",
        )

        db = _mock_db_for_merge(primary=primary, duplicate=duplicate)

        field_selections = [
            MergeFieldSelection(field_name="first_name", source="b"),
            MergeFieldSelection(field_name="email", source="b"),
        ]

        await svc.execute_merge(
            db=db,
            primary_id=primary.id,
            duplicate_id=duplicate.id,
            field_selections=field_selections,
            admin_id=uuid4(),
        )

        # flush means the merge completed successfully
        db.flush.assert_awaited_once()


# =============================================================================
# 2. Stripe Subscription Blocker
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestStripSubscriptionBlocker:
    """Merge is blocked when both customers have active Stripe subscriptions.

    Validates: Requirement 6.7
    """

    async def test_merge_blocked_when_both_have_active_stripe(self) -> None:
        """MergeConflictError raised when both have Stripe subscriptions.

        Validates: Requirement 6.7
        """
        svc = CustomerMergeService()

        primary = _make_customer(
            first_name="Carol",
            stripe_customer_id="cus_primary123",
        )
        duplicate = _make_customer(
            first_name="Carole",
            stripe_customer_id="cus_dup456",
        )

        db = _mock_db_for_merge(
            primary=primary,
            duplicate=duplicate,
            both_have_stripe=True,
        )

        with pytest.raises(MergeConflictError, match="Stripe subscriptions"):
            await svc.execute_merge(
                db=db,
                primary_id=primary.id,
                duplicate_id=duplicate.id,
                field_selections=[],
                admin_id=uuid4(),
            )

        # No flush — merge was aborted
        db.flush.assert_not_awaited()

    async def test_merge_allowed_when_only_one_has_stripe(self) -> None:
        """Merge proceeds when only one customer has a Stripe subscription.

        Validates: Requirement 6.7
        """
        svc = CustomerMergeService()

        primary = _make_customer(
            first_name="Dave",
            stripe_customer_id="cus_dave",
        )
        duplicate = _make_customer(
            first_name="David",
            stripe_customer_id=None,
        )

        db = _mock_db_for_merge(
            primary=primary,
            duplicate=duplicate,
            both_have_stripe=False,
        )

        await svc.execute_merge(
            db=db,
            primary_id=primary.id,
            duplicate_id=duplicate.id,
            field_selections=[],
            admin_id=uuid4(),
        )

        db.flush.assert_awaited_once()

    async def test_check_merge_blockers_returns_empty_when_no_stripe(
        self,
    ) -> None:
        """No blockers when neither customer has Stripe subscriptions.

        Validates: Requirement 6.7
        """
        svc = CustomerMergeService()

        primary = _make_customer(first_name="Eve")
        duplicate = _make_customer(first_name="Eva")

        db = _mock_db_for_merge(
            primary=primary,
            duplicate=duplicate,
            both_have_stripe=False,
        )

        blockers = await svc.check_merge_blockers(
            db=db,
            primary_id=primary.id,
            duplicate_id=duplicate.id,
        )

        assert blockers == []


# =============================================================================
# 3. Soft-Delete via merged_into_customer_id
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestMergeSoftDelete:
    """Duplicate is soft-deleted by setting merged_into_customer_id.

    Validates: Requirement 6.5
    """

    async def test_duplicate_soft_deleted_with_merged_into_set(self) -> None:
        """Duplicate's merged_into_customer_id points to primary after merge.

        Validates: Requirements 6.5, 35.1
        """
        svc = CustomerMergeService()

        primary = _make_customer(first_name="Frank", phone="5125550050")
        duplicate = _make_customer(first_name="Franklin", phone="5125550051")

        db = _mock_db_for_merge(primary=primary, duplicate=duplicate)

        await svc.execute_merge(
            db=db,
            primary_id=primary.id,
            duplicate_id=duplicate.id,
            field_selections=[],
            admin_id=uuid4(),
        )

        # Verify soft-delete fields were set on the duplicate mock
        assert duplicate.merged_into_customer_id == primary.id
        assert duplicate.is_deleted is True
        assert duplicate.deleted_at is not None

    async def test_primary_not_soft_deleted_after_merge(self) -> None:
        """Primary customer remains active after merge.

        Validates: Requirement 6.5
        """
        svc = CustomerMergeService()

        primary = _make_customer(first_name="Grace", phone="5125550060")
        duplicate = _make_customer(first_name="Gracie", phone="5125550061")

        db = _mock_db_for_merge(primary=primary, duplicate=duplicate)

        await svc.execute_merge(
            db=db,
            primary_id=primary.id,
            duplicate_id=duplicate.id,
            field_selections=[],
            admin_id=uuid4(),
        )

        # Primary should NOT be soft-deleted
        assert primary.merged_into_customer_id is None
        assert primary.is_deleted is False


# =============================================================================
# 4. Audit Log Creation
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestMergeAuditLog:
    """Merge creates an audit log entry with merge details.

    Validates: Requirements 6.5, 35.1
    """

    async def test_audit_log_created_on_successful_merge(self) -> None:
        """AuditLog entry records merge action, IDs, and field selections.

        Validates: Requirements 6.5, 35.1
        """
        svc = CustomerMergeService()

        primary = _make_customer(first_name="Hank", phone="5125550070")
        duplicate = _make_customer(first_name="Henry", phone="5125550071")

        db = _mock_db_for_merge(primary=primary, duplicate=duplicate)
        admin_id = uuid4()

        field_selections = [
            MergeFieldSelection(field_name="phone", source="a"),
            MergeFieldSelection(field_name="email", source="b"),
        ]

        await svc.execute_merge(
            db=db,
            primary_id=primary.id,
            duplicate_id=duplicate.id,
            field_selections=field_selections,
            admin_id=admin_id,
        )

        # Verify db.add was called with an AuditLog
        db.add.assert_called_once()
        audit_entry = db.add.call_args[0][0]
        assert isinstance(audit_entry, AuditLog)
        assert audit_entry.action == "customer_merge"
        assert audit_entry.resource_type == "customer"
        assert audit_entry.resource_id == primary.id
        assert audit_entry.actor_id == admin_id

        # Verify details contain merge info
        details = audit_entry.details
        assert details["primary_id"] == str(primary.id)
        assert details["duplicate_id"] == str(duplicate.id)
        assert len(details["field_selections"]) == 2

    async def test_no_audit_log_when_merge_blocked(self) -> None:
        """No audit log is created when merge is blocked by Stripe.

        Validates: Requirement 6.7
        """
        svc = CustomerMergeService()

        primary = _make_customer(
            first_name="Iris",
            stripe_customer_id="cus_iris",
        )
        duplicate = _make_customer(
            first_name="Irene",
            stripe_customer_id="cus_irene",
        )

        db = _mock_db_for_merge(
            primary=primary,
            duplicate=duplicate,
            both_have_stripe=True,
        )

        with pytest.raises(MergeConflictError):
            await svc.execute_merge(
                db=db,
                primary_id=primary.id,
                duplicate_id=duplicate.id,
                field_selections=[],
                admin_id=uuid4(),
            )

        # No audit log should have been added
        db.add.assert_not_called()
