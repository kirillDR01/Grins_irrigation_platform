"""Repository for SmsConsentRecord database operations.

Read-only façade over :class:`SmsConsentRecord` for batch consent checks.
The underlying table is INSERT-ONLY (TCPA compliance) — writes go through
``grins_platform.services.sms.consent``. This repo exists so that services
which need to ask "given a list of customer_ids, which have opted out?"
can do so in a single query.

Validates: H-11 (bughunt 2026-04-16) — batch SMS-consent pre-filter.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import select

from grins_platform.log_config import LoggerMixin
from grins_platform.models.sms_consent_record import SmsConsentRecord

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SmsConsentRepository(LoggerMixin):
    """Repository for SmsConsentRecord queries.

    Validates: H-11 (bughunt 2026-04-16).
    """

    DOMAIN = "database"

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session."""
        super().__init__()
        self.session = session

    async def get_opted_out_customer_ids(
        self,
        customer_ids: list[UUID],
    ) -> set[UUID]:
        """Return the subset of the given customer_ids that have opted out of SMS.

        A single query against ``sms_consent_records``. Customers with no
        consent record are treated as "not opted out" (consistent with
        existing behavior in ``send_lien_notice`` / CR-5).

        A customer is considered opted out if they have any
        ``SmsConsentRecord`` row with ``consent_given = FALSE`` — that
        matches the ``text_stop`` revocation pattern and CR-5's per-customer
        check.

        Args:
            customer_ids: List of customer UUIDs to check. Empty list returns
                an empty set with no query executed.

        Returns:
            Set of customer_ids (subset of input) that have opted out.
        """
        if not customer_ids:
            return set()

        self.log_started(
            "get_opted_out_customer_ids",
            count=len(customer_ids),
        )

        # SELECT DISTINCT customer_id FROM sms_consent_records
        # WHERE customer_id IN (:ids) AND consent_given = FALSE
        stmt = (
            select(SmsConsentRecord.customer_id)
            .where(
                SmsConsentRecord.customer_id.in_(customer_ids),
                SmsConsentRecord.consent_given.is_(False),
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        opted_out: set[UUID] = {
            row_id for row_id in result.scalars().all() if row_id is not None
        }

        self.log_completed(
            "get_opted_out_customer_ids",
            count=len(customer_ids),
            opted_out_count=len(opted_out),
        )
        return opted_out

    async def get_latest_for_customer(
        self,
        customer_id: UUID,
    ) -> SmsConsentRecord | None:
        """Return the most recent SmsConsentRecord for a customer.

        The consent table is INSERT-ONLY so the "current" state for a
        customer is the row with the newest ``created_at``. Callers decide
        whether to interpret ``consent_given=False`` as opted-out; this
        repo does not filter.

        Args:
            customer_id: The customer UUID.

        Returns:
            The newest SmsConsentRecord or None if the customer has no rows.
        """
        self.log_started(
            "get_latest_for_customer",
            customer_id=str(customer_id),
        )
        result = await self.session.execute(
            select(SmsConsentRecord)
            .where(SmsConsentRecord.customer_id == customer_id)
            .order_by(SmsConsentRecord.created_at.desc())
            .limit(1),
        )
        row: SmsConsentRecord | None = result.scalar_one_or_none()
        self.log_completed(
            "get_latest_for_customer",
            found=row is not None,
        )
        return row

    async def list_by_customer(
        self,
        customer_id: UUID,
        limit: int = 50,
    ) -> list[SmsConsentRecord]:
        """Return a customer's consent rows newest-first.

        Drives the consent-history timeline on the frontend. Ordered by
        ``consent_timestamp`` DESC so the current state sits at the top.

        Args:
            customer_id: Customer UUID.
            limit: Maximum number of rows to return (default 50).

        Returns:
            List of :class:`SmsConsentRecord` rows, newest first.
        """
        self.log_started(
            "list_by_customer",
            customer_id=str(customer_id),
            limit=limit,
        )
        result = await self.session.execute(
            select(SmsConsentRecord)
            .where(SmsConsentRecord.customer_id == customer_id)
            .order_by(SmsConsentRecord.consent_timestamp.desc())
            .limit(limit),
        )
        rows = list(result.scalars().all())
        self.log_completed("list_by_customer", count=len(rows))
        return rows
