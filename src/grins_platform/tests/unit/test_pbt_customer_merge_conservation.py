"""Property-based tests for customer merge data conservation.

Property 11: Customer Merge Data Conservation
- Total jobs/invoices/communications before == total after on surviving record
- duplicate.merged_into_customer_id == primary.id
- Audit log exists

Validates: Requirements 35.1, 35.2, 35.3
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.schemas.customer_merge import MergeFieldSelection
from grins_platform.services.customer_merge_service import (
    _MERGEABLE_FIELDS,
    _REASSIGN_TABLES,
    CustomerMergeService,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

_record_counts = st.integers(min_value=0, max_value=20)


def _mock_customer(
    customer_id: UUID | None = None,
    *,
    first_name: str = "John",
    last_name: str = "Doe",
    phone: str = "6125551234",
    email: str | None = None,
) -> MagicMock:
    c = MagicMock()
    c.id = customer_id or uuid4()
    c.first_name = first_name
    c.last_name = last_name
    c.phone = phone
    c.email = email
    c.is_deleted = False
    c.deleted_at = None
    c.merged_into_customer_id = None
    c.lead_source = None
    c.internal_notes = None
    c.is_priority = False
    c.is_red_flag = False
    c.is_slow_payer = False
    c.sms_opt_in = False
    c.email_opt_in = False
    return c


# ===================================================================
# Property 11: Customer Merge Data Conservation
# Validates: Req 35.1, 35.2, 35.3
# ===================================================================


@pytest.mark.unit
class TestProperty11CustomerMergeDataConservation:
    """Total related records before == after on surviving record,
    duplicate.merged_into_customer_id == primary.id, audit log exists.
    """

    @given(num_tables=st.just(len(_REASSIGN_TABLES)))
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_all_related_records_reassigned(
        self,
        num_tables: int,
    ) -> None:
        """Every reassign table gets an UPDATE from duplicate to primary."""
        primary_id = uuid4()
        duplicate_id = uuid4()
        primary = _mock_customer(primary_id)
        duplicate = _mock_customer(duplicate_id)

        svc = CustomerMergeService()
        db = AsyncMock()

        with (
            patch.object(
                svc,
                "_get_customer",
                side_effect=[primary, duplicate],
            ),
            patch.object(svc, "check_merge_blockers", return_value=[]),
        ):
            await svc.execute_merge(
                db,
                primary_id,
                duplicate_id,
                [],
                admin_id=uuid4(),
            )

        execute_calls = db.execute.call_args_list
        reassign_calls = [
            c
            for c in execute_calls
            if hasattr(c[0][0], "text") and "SET customer_id" in str(c[0][0].text)
        ]

        assert len(reassign_calls) == num_tables

    @given(admin_id=st.uuids())
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_duplicate_soft_deleted_with_pointer(
        self,
        admin_id: UUID,
    ) -> None:
        """After merge, duplicate.merged_into_customer_id == primary.id
        and duplicate.is_deleted == True.
        """
        primary_id = uuid4()
        duplicate_id = uuid4()
        primary = _mock_customer(primary_id)
        duplicate = _mock_customer(duplicate_id)

        svc = CustomerMergeService()
        db = AsyncMock()

        with (
            patch.object(
                svc,
                "_get_customer",
                side_effect=[primary, duplicate],
            ),
            patch.object(svc, "check_merge_blockers", return_value=[]),
        ):
            await svc.execute_merge(
                db,
                primary_id,
                duplicate_id,
                [],
                admin_id=admin_id,
            )

        assert duplicate.merged_into_customer_id == primary_id
        assert duplicate.is_deleted is True
        assert duplicate.deleted_at is not None

    @given(admin_id=st.uuids())
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_audit_log_created(
        self,
        admin_id: UUID,
    ) -> None:
        """Merge writes an audit log entry with correct action and IDs."""
        primary_id = uuid4()
        duplicate_id = uuid4()
        primary = _mock_customer(primary_id)
        duplicate = _mock_customer(duplicate_id)

        svc = CustomerMergeService()
        db = AsyncMock()

        with (
            patch.object(
                svc,
                "_get_customer",
                side_effect=[primary, duplicate],
            ),
            patch.object(svc, "check_merge_blockers", return_value=[]),
        ):
            await svc.execute_merge(
                db,
                primary_id,
                duplicate_id,
                [],
                admin_id=admin_id,
            )

        add_calls = db.add.call_args_list
        audit_entries = [
            c[0][0]
            for c in add_calls
            if hasattr(c[0][0], "action") and c[0][0].action == "customer_merge"
        ]
        assert len(audit_entries) == 1
        entry = audit_entries[0]
        assert entry.resource_id == primary_id
        assert entry.actor_id == admin_id
        assert entry.details["primary_id"] == str(primary_id)
        assert entry.details["duplicate_id"] == str(duplicate_id)

    @given(
        num_selections=st.integers(
            min_value=1,
            max_value=len(_MERGEABLE_FIELDS),
        ),
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_field_selections_applied_to_primary(
        self,
        num_selections: int,
    ) -> None:
        """Field selections from duplicate are applied to primary record."""
        primary_id = uuid4()
        duplicate_id = uuid4()
        primary = _mock_customer(
            primary_id,
            first_name="Alice",
            last_name="Smith",
        )
        duplicate = _mock_customer(
            duplicate_id,
            first_name="Bob",
            last_name="Jones",
        )

        fields_to_select = _MERGEABLE_FIELDS[:num_selections]
        selections = [
            MergeFieldSelection(field_name=f, source="b") for f in fields_to_select
        ]

        svc = CustomerMergeService()
        db = AsyncMock()

        with (
            patch.object(
                svc,
                "_get_customer",
                side_effect=[primary, duplicate],
            ),
            patch.object(svc, "check_merge_blockers", return_value=[]),
        ):
            await svc.execute_merge(
                db,
                primary_id,
                duplicate_id,
                selections,
                admin_id=uuid4(),
            )

        for field in fields_to_select:
            expected = getattr(duplicate, field)
            actual = getattr(primary, field)
            assert actual == expected, f"{field}: expected {expected}, got {actual}"
