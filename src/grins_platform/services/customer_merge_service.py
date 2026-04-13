"""Customer merge service for combining duplicate customer records.

Validates: CRM Changes Update 2 Req 6.1-6.13
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import TextClause, func, select, text, update

from grins_platform.exceptions import (
    CustomerNotFoundError,
    MergeConflictError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.audit_log import AuditLog
from grins_platform.models.customer import Customer
from grins_platform.models.customer_merge_candidate import CustomerMergeCandidate
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.schemas.customer_merge import (
    MergeFieldSelection,
    MergePreviewResponse,
)

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession

# Tables with customer_id FK to reassign during merge
_REASSIGN_TABLES = [
    "jobs",
    "invoices",
    "properties",
    "sent_messages",
    "communications",
    "service_agreements",
    "customer_photos",
    "customer_documents",
    "estimates",
    "sales_entries",
    "contract_renewal_proposals",
]

# Customer fields eligible for merge field selection
_MERGEABLE_FIELDS = [
    "first_name",
    "last_name",
    "phone",
    "email",
    "lead_source",
    "internal_notes",
    "is_priority",
    "is_red_flag",
    "is_slow_payer",
    "sms_opt_in",
    "email_opt_in",
]


def _reassign_stmt(
    table_name: str,
    from_id: UUID,
    to_id: UUID,
) -> TextClause:
    """Build UPDATE statement to reassign customer_id."""
    return text(
        f"UPDATE {table_name} SET customer_id = :to_id "  # noqa: S608
        "WHERE customer_id = :from_id",
    ).bindparams(to_id=to_id, from_id=from_id)


class CustomerMergeService(LoggerMixin):
    """Merges duplicate customer records with data conservation.

    Validates: CRM Changes Update 2 Req 6.1-6.13
    """

    DOMAIN = "customer"

    async def check_merge_blockers(
        self,
        db: AsyncSession,
        primary_id: UUID,
        duplicate_id: UUID,
    ) -> list[str]:
        """Check for conditions that block a merge.

        Blocks if both customers have active Stripe subscriptions.

        Validates: Req 6.7
        """
        self.log_started(
            "check_merge_blockers",
            primary_id=str(primary_id),
            duplicate_id=str(duplicate_id),
        )

        stmt = (
            select(
                ServiceAgreement.customer_id,
                func.count().label("cnt"),
            )
            .where(
                ServiceAgreement.customer_id.in_(
                    [primary_id, duplicate_id],
                ),
                ServiceAgreement.stripe_subscription_id.isnot(None),
                ServiceAgreement.status.in_(["active", "pending"]),
            )
            .group_by(ServiceAgreement.customer_id)
        )
        result = await db.execute(stmt)
        rows = result.all()

        blockers: list[str] = []
        if len(rows) >= 2:
            blockers.append(
                "Both customers have active Stripe subscriptions. "
                "Cancel one subscription before merging.",
            )

        self.log_completed(
            "check_merge_blockers",
            blocker_count=len(blockers),
        )
        return blockers

    async def preview_merge(
        self,
        db: AsyncSession,
        primary_id: UUID,
        duplicate_id: UUID,
        field_selections: list[MergeFieldSelection] | None = None,
    ) -> MergePreviewResponse:
        """Preview merge result without executing.

        Validates: Req 6.2, 6.3
        """
        self.log_started(
            "preview_merge",
            primary_id=str(primary_id),
            duplicate_id=str(duplicate_id),
        )

        primary = await self._get_customer(db, primary_id)
        duplicate = await self._get_customer(db, duplicate_id)

        blockers = await self.check_merge_blockers(
            db,
            primary_id,
            duplicate_id,
        )
        merged_fields = self._compute_merged_fields(
            primary,
            duplicate,
            field_selections or [],
        )
        counts = await self._count_related_records(db, duplicate_id)

        self.log_completed("preview_merge")
        return MergePreviewResponse(
            primary_id=primary_id,
            duplicate_id=duplicate_id,
            merged_fields=merged_fields,
            jobs_to_reassign=counts["jobs"],
            invoices_to_reassign=counts["invoices"],
            properties_to_reassign=counts["properties"],
            communications_to_reassign=counts["communications"],
            agreements_to_reassign=counts["agreements"],
            blockers=blockers,
        )

    async def execute_merge(
        self,
        db: AsyncSession,
        primary_id: UUID,
        duplicate_id: UUID,
        field_selections: list[MergeFieldSelection],
        admin_id: UUID | None = None,
    ) -> None:
        """Execute customer merge with full data reassignment.

        Validates: Req 6.4, 6.5, 6.6, 6.8, 6.9, 6.10, 6.11
        """
        self.log_started(
            "execute_merge",
            primary_id=str(primary_id),
            duplicate_id=str(duplicate_id),
        )

        primary = await self._get_customer(db, primary_id)
        duplicate = await self._get_customer(db, duplicate_id)

        # Check blockers
        blockers = await self.check_merge_blockers(
            db,
            primary_id,
            duplicate_id,
        )
        if blockers:
            self.log_rejected("execute_merge", reason=blockers[0])
            raise MergeConflictError(blockers[0])

        # Apply field selections to primary
        merged_fields = self._compute_merged_fields(
            primary,
            duplicate,
            field_selections,
        )
        for field, value in merged_fields.items():
            if hasattr(primary, field):
                setattr(primary, field, value)

        # Reassign all related records from duplicate to primary
        for table_name in _REASSIGN_TABLES:
            await db.execute(
                _reassign_stmt(table_name, duplicate_id, primary_id),
            )

        # Soft-delete duplicate
        duplicate.merged_into_customer_id = primary_id
        duplicate.is_deleted = True
        duplicate.deleted_at = datetime.now()

        # Resolve any pending merge candidates for this pair
        await db.execute(
            update(CustomerMergeCandidate)
            .where(
                CustomerMergeCandidate.status == "pending",
                (
                    (CustomerMergeCandidate.customer_a_id == primary_id)
                    & (CustomerMergeCandidate.customer_b_id == duplicate_id)
                )
                | (
                    (CustomerMergeCandidate.customer_a_id == duplicate_id)
                    & (CustomerMergeCandidate.customer_b_id == primary_id)
                ),
            )
            .values(
                status="merged",
                resolved_at=func.now(),
                resolution="merged",
            ),
        )

        # Write audit log
        db.add(
            AuditLog(
                actor_id=admin_id,
                action="customer_merge",
                resource_type="customer",
                resource_id=primary_id,
                details={
                    "primary_id": str(primary_id),
                    "duplicate_id": str(duplicate_id),
                    "field_selections": [
                        {
                            "field": fs.field_name,
                            "source": fs.source,
                        }
                        for fs in field_selections
                    ],
                },
            ),
        )

        await db.flush()
        self.log_completed(
            "execute_merge",
            primary_id=str(primary_id),
            duplicate_id=str(duplicate_id),
        )

    # -- Private helpers ------------------------------------------------

    @staticmethod
    async def _get_customer(
        db: AsyncSession,
        customer_id: UUID,
    ) -> Customer:
        stmt = select(Customer).where(
            Customer.id == customer_id,
            Customer.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        customer: Customer | None = result.scalar_one_or_none()
        if not customer:
            raise CustomerNotFoundError(customer_id)
        return customer

    @staticmethod
    def _compute_merged_fields(
        primary: Customer,
        duplicate: Customer,
        field_selections: list[MergeFieldSelection],
    ) -> dict[str, object]:
        """Compute merged field values.

        Use admin selection if provided, otherwise default to
        non-empty value (primary wins ties).
        """
        selection_map = {fs.field_name: fs.source for fs in field_selections}
        merged: dict[str, object] = {}

        for field in _MERGEABLE_FIELDS:
            p_val = getattr(primary, field, None)
            d_val = getattr(duplicate, field, None)

            if field in selection_map:
                merged[field] = p_val if selection_map[field] == "a" else d_val
            elif p_val in (None, "", False) and d_val not in (None, "", False):
                merged[field] = d_val
            else:
                merged[field] = p_val

        return merged

    @staticmethod
    async def _count_related_records(
        db: AsyncSession,
        duplicate_id: UUID,
    ) -> dict[str, int]:
        """Count records that would be reassigned."""
        counts: dict[str, int] = {}
        table_map = {
            "jobs": "jobs",
            "invoices": "invoices",
            "properties": "properties",
            "communications": "sent_messages",
            "agreements": "service_agreements",
        }
        for key, table in table_map.items():
            result = await db.execute(
                text(
                    f"SELECT count(*) FROM {table} "  # noqa: S608
                    "WHERE customer_id = :cid",
                ),
                {"cid": duplicate_id},
            )
            counts[key] = result.scalar() or 0

        return counts
