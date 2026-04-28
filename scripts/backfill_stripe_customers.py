#!/usr/bin/env python3
"""One-time backfill: ensure every Grin's customer has a ``stripe_customer_id``.

Stripe sends payment receipts only when a Customer with an email is on
file, and the Stripe Payment Links feature relies on the Grin's customer
already being linked to a Stripe Customer so reconciliation metadata
lines up. Some legacy Grin's customers were created before that linkage
was wired up; this script finds them and creates a matching Stripe
Customer (with metadata.grins_customer_id) for each.

Idempotent: rows that already have a ``stripe_customer_id`` are skipped.

================================================================
DO NOT RUN AGAINST PRODUCTION DATA YET. This script is staged for
the prod cutover phase of the Stripe Payment Links rollout. Until
that point, run only against the dev/staging database, and only
when the dev Stripe key is loaded (``sk_test_*``). The dev Stripe
account has its own customer namespace so any IDs created here will
NOT collide with the live account.
================================================================

Usage::

    # Dry run (default — counts what would change, doesn't touch Stripe)
    uv run python scripts/backfill_stripe_customers.py

    # Real run with explicit confirmation
    uv run python scripts/backfill_stripe_customers.py --execute

    # Real run capped at first N rows for canary testing
    uv run python scripts/backfill_stripe_customers.py --execute --limit 5

Validates: Stripe Payment Links plan §Phase 1.3.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from grins_platform.database import DatabaseManager
from grins_platform.exceptions import (
    CustomerNotFoundError,
    MergeConflictError,
)
from grins_platform.log_config import get_logger
from grins_platform.models.customer import Customer
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.stripe_config import StripeSettings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

# Stripe limits live + test keys to ~100 reads/sec and ~25 writes/sec.
# Sleep between writes leaves headroom under the write budget and avoids
# accidental rate-limit retries on a long backfill.
_RATE_LIMIT_SLEEP_SEC = 0.05


@dataclass
class _BackfillStats:
    candidates: int = 0
    skipped_already_linked: int = 0
    created: int = 0
    failed: int = 0


async def _candidates(session: AsyncSession, *, limit: int | None) -> list[Customer]:
    stmt = select(Customer).where(
        Customer.stripe_customer_id.is_(None),
        Customer.is_deleted.is_(False),
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def _backfill(*, execute: bool, limit: int | None) -> _BackfillStats:
    stats = _BackfillStats()
    settings = StripeSettings()
    if execute and not settings.is_configured:
        logger.error(
            "backfill.stripe_customers.aborted",
            reason="stripe_not_configured",
        )
        msg = "STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET not configured"
        raise SystemExit(msg)

    db_manager = DatabaseManager()
    try:
        async with db_manager.session_factory() as session:
            customers = await _candidates(session, limit=limit)
            stats.candidates = len(customers)
            logger.info(
                "backfill.stripe_customers.scan_completed",
                candidates=stats.candidates,
                execute=execute,
            )

            if not execute:
                return stats

            customer_repo = CustomerRepository(session)
            property_repo = PropertyRepository(session)
            service = CustomerService(
                repository=customer_repo,
                property_repository=property_repo,
            )

            for customer in customers:
                try:
                    new_id = await service.get_or_create_stripe_customer(customer.id)
                    if customer.stripe_customer_id == new_id:
                        # Race: another process linked it concurrently.
                        stats.skipped_already_linked += 1
                    else:
                        stats.created += 1
                    await session.commit()
                except (CustomerNotFoundError, MergeConflictError) as exc:
                    stats.failed += 1
                    logger.warning(
                        "backfill.stripe_customers.row_failed",
                        customer_id=str(customer.id),
                        error=str(exc),
                    )
                    await session.rollback()

                time.sleep(_RATE_LIMIT_SLEEP_SEC)
    finally:
        await db_manager.close()
    return stats


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually create Stripe Customers. Without this flag the "
        "script counts candidates and exits without touching Stripe.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on candidates processed (canary mode).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    stats = asyncio.run(_backfill(execute=args.execute, limit=args.limit))
    mode = "EXECUTE" if args.execute else "DRY-RUN"
    print(
        f"[{mode}] Stripe customer backfill complete: "
        f"candidates={stats.candidates} "
        f"created={stats.created} "
        f"already_linked={stats.skipped_already_linked} "
        f"failed={stats.failed}",
    )
    return 0 if stats.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
