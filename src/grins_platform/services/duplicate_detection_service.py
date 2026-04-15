"""Customer duplicate detection service with weighted scoring.

Computes a 0-100 confidence score for customer pairs using phone, email,
name similarity, address, and ZIP+last-name signals. A nightly sweep
batch-processes all active customers and upserts results into
customer_merge_candidates.

Validates: CRM Changes Update 2 Req 5.1-5.8
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from grins_platform.log_config import LoggerMixin
from grins_platform.models.customer import Customer
from grins_platform.models.customer_merge_candidate import CustomerMergeCandidate
from grins_platform.services.sms.phone_normalizer import (
    PhoneNormalizationError,
    normalize_to_e164,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# -- Signal weights (Req 5.1) ------------------------------------------
WEIGHT_PHONE = 60
WEIGHT_EMAIL = 50
WEIGHT_NAME = 25
WEIGHT_ADDRESS = 20
WEIGHT_ZIP_LAST = 10
MAX_SCORE = 100
NAME_SIMILARITY_THRESHOLD = 0.92


# -- Jaro-Winkler implementation ---------------------------------------
def _jaro_similarity(s1: str, s2: str) -> float:
    """Compute Jaro similarity between two strings."""
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_distance = max(max(len1, len2) // 2 - 1, 0)

    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    return (
        matches / len1 + matches / len2 + (matches - transpositions / 2) / matches
    ) / 3


def jaro_winkler_similarity(
    s1: str,
    s2: str,
    prefix_weight: float = 0.1,
) -> float:
    """Compute Jaro-Winkler similarity between two strings."""
    jaro = _jaro_similarity(s1, s2)
    prefix_len = 0
    for i in range(min(4, len(s1), len(s2))):
        if s1[i] == s2[i]:
            prefix_len += 1
        else:
            break
    return jaro + prefix_len * prefix_weight * (1 - jaro)


# -- Normalization helpers ----------------------------------------------
_NON_ALNUM = re.compile(r"[^a-z0-9 ]")


def _normalize_name(name: str) -> str:
    """Lowercase, strip accents, collapse whitespace."""
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_only = nfkd.encode("ascii", "ignore").decode("ascii")
    return _NON_ALNUM.sub("", ascii_only.lower()).strip()


def _normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    return email.strip().lower()


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    try:
        return normalize_to_e164(phone)
    except PhoneNormalizationError:
        return None


def _normalize_address(address: str | None) -> str | None:
    if not address:
        return None
    addr = address.strip().lower()
    for full, abbr in [
        ("street", "st"),
        ("avenue", "ave"),
        ("boulevard", "blvd"),
        ("drive", "dr"),
        ("lane", "ln"),
        ("road", "rd"),
        ("court", "ct"),
        ("place", "pl"),
        ("circle", "cir"),
    ]:
        addr = re.sub(rf"\b{full}\b", abbr, addr)
        addr = re.sub(rf"\b{abbr}\.\b", abbr, addr)
    return re.sub(r"\s+", " ", addr).strip()


# -- Service ------------------------------------------------------------
class DuplicateDetectionService(LoggerMixin):
    """Detects potential duplicate customer records via weighted scoring.

    Validates: CRM Changes Update 2 Req 5.1-5.8
    """

    DOMAIN = "customer"

    # -- Public API -----------------------------------------------------

    def compute_score(
        self,
        customer_a: Customer,
        customer_b: Customer,
    ) -> tuple[int, dict[str, Any]]:
        """Compute duplicate confidence score for a customer pair.

        Args:
            customer_a: First customer record.
            customer_b: Second customer record.

        Returns:
            Tuple of (score 0-100, match_signals dict).

        Validates: Req 5.1
        """
        score = 0
        signals: dict[str, Any] = {}

        # Phone match (+60)
        phone_a = _normalize_phone(customer_a.phone)
        phone_b = _normalize_phone(customer_b.phone)
        if phone_a and phone_b and phone_a == phone_b:
            score += WEIGHT_PHONE
            signals["phone"] = True

        # Email match (+50)
        email_a = _normalize_email(customer_a.email)
        email_b = _normalize_email(customer_b.email)
        if email_a and email_b and email_a == email_b:
            score += WEIGHT_EMAIL
            signals["email"] = True

        # Name similarity (+25)
        name_a = _normalize_name(
            f"{customer_a.first_name} {customer_a.last_name}",
        )
        name_b = _normalize_name(
            f"{customer_b.first_name} {customer_b.last_name}",
        )
        if name_a and name_b:
            sim = jaro_winkler_similarity(name_a, name_b)
            if sim >= NAME_SIMILARITY_THRESHOLD:
                score += WEIGHT_NAME
                signals["name_similarity"] = round(sim, 4)

        # Address match (+20)
        addr_a = self._get_primary_address(customer_a)
        addr_b = self._get_primary_address(customer_b)
        if addr_a and addr_b and addr_a == addr_b:
            score += WEIGHT_ADDRESS
            signals["address"] = True

        # ZIP + last name match (+10)
        zip_a = self._get_primary_zip(customer_a)
        zip_b = self._get_primary_zip(customer_b)
        last_a = _normalize_name(customer_a.last_name)
        last_b = _normalize_name(customer_b.last_name)
        zip_last_match = (
            zip_a
            and zip_b
            and zip_a == zip_b
            and last_a
            and last_b
            and last_a == last_b
        )
        if zip_last_match:
            score += WEIGHT_ZIP_LAST
            signals["zip_last_name"] = True

        score = min(score, MAX_SCORE)
        return score, signals

    async def run_nightly_sweep(self, db: AsyncSession) -> int:
        """Batch-compute scores for pre-filtered candidate pairs.

        Pre-filters on shared phone, email, or last name to avoid
        O(n^2) full cross-join. Upserts into customer_merge_candidates.

        Args:
            db: Async database session.

        Returns:
            Number of candidates upserted.

        Validates: Req 5.6, 5.7
        """
        self.log_started("nightly_sweep")

        stmt = (
            select(Customer)
            .where(
                Customer.is_deleted.is_(False),
                Customer.merged_into_customer_id.is_(None),
            )
            .order_by(Customer.id)
        )
        result = await db.execute(stmt)
        customers = list(result.scalars().all())

        self.logger.info(
            "customer.duplicatedetectionservice.sweep_candidates",
            total_customers=len(customers),
        )

        # Build lookup indexes for pre-filtering
        by_phone: dict[str, list[Customer]] = {}
        by_email: dict[str, list[Customer]] = {}
        by_last_name: dict[str, list[Customer]] = {}

        for c in customers:
            phone = _normalize_phone(c.phone)
            if phone:
                by_phone.setdefault(phone, []).append(c)
            email = _normalize_email(c.email)
            if email:
                by_email.setdefault(email, []).append(c)
            last = _normalize_name(c.last_name)
            if last:
                by_last_name.setdefault(last, []).append(c)

        # Collect unique candidate pairs from shared signals
        seen_pairs: set[tuple[UUID, UUID]] = set()
        candidate_pairs: list[tuple[Customer, Customer]] = []

        for group in [
            *by_phone.values(),
            *by_email.values(),
            *by_last_name.values(),
        ]:
            if len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    a, b = group[i], group[j]
                    pair_key = (min(a.id, b.id), max(a.id, b.id))
                    if pair_key not in seen_pairs:
                        seen_pairs.add(pair_key)
                        candidate_pairs.append((a, b))

        # Score and upsert
        upserted = 0
        for a, b in candidate_pairs:
            score, signals = self.compute_score(a, b)
            if score < 50:
                continue

            ca_id, cb_id = (a.id, b.id) if a.id < b.id else (b.id, a.id)

            upsert_stmt = pg_insert(
                CustomerMergeCandidate,
            ).values(
                customer_a_id=ca_id,
                customer_b_id=cb_id,
                score=score,
                match_signals=signals,
                status="pending",
            )
            upsert_stmt = upsert_stmt.on_conflict_do_update(
                constraint="uq_merge_candidates_pair",
                set_={
                    "score": score,
                    "match_signals": signals,
                    "status": "pending",
                },
            )
            await db.execute(upsert_stmt)
            upserted += 1

        await db.flush()
        self.log_completed("nightly_sweep", upserted=upserted)
        return upserted

    async def get_review_queue(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[Sequence[CustomerMergeCandidate], int]:
        """Get paginated review queue sorted by score descending.

        Args:
            db: Async database session.
            skip: Number of records to skip.
            limit: Maximum records to return.

        Returns:
            Tuple of (candidates list, total count).

        Validates: Req 5.6
        """
        self.log_started("get_review_queue", skip=skip, limit=limit)

        base = CustomerMergeCandidate.status == "pending"

        count_stmt = (
            select(func.count()).select_from(CustomerMergeCandidate).where(base)
        )
        total = (await db.execute(count_stmt)).scalar() or 0

        stmt = (
            select(CustomerMergeCandidate)
            .where(base)
            .order_by(CustomerMergeCandidate.score.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        candidates = list(result.scalars().all())

        self.log_completed(
            "get_review_queue",
            total=total,
            returned=len(candidates),
        )
        return candidates, int(total)

    # -- Private helpers ------------------------------------------------

    @staticmethod
    def _get_primary_address(customer: Customer) -> str | None:
        """Get normalized primary property address."""
        if not customer.properties:
            return None
        primary = next(
            (p for p in customer.properties if p.is_primary),
            customer.properties[0],
        )
        return _normalize_address(primary.address)

    @staticmethod
    def _get_primary_zip(customer: Customer) -> str | None:
        """Get primary property ZIP code."""
        if not customer.properties:
            return None
        primary = next(
            (p for p in customer.properties if p.is_primary),
            customer.properties[0],
        )
        return primary.zip_code.strip() if primary.zip_code else None
