"""Property test for consent token linkage.

Property 7: Consent Token Linkage
For any pre-checkout consent flow followed by checkout.session.completed
with same consent_token, orphaned records (customer_id IS NULL) are linked
to new Customer and ServiceAgreement.

Validates: Requirements 8.7, 30.4
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.services.compliance_service import ComplianceService

# Strategies
consent_tokens = st.uuids()
customer_ids = st.uuids()
agreement_ids = st.uuids()
orphan_counts = st.integers(min_value=1, max_value=5)


def _make_orphaned_disclosure(consent_token: object) -> MagicMock:
    """Create an orphaned disclosure record (customer_id=None)."""
    record = MagicMock()
    record.id = uuid4()
    record.customer_id = None
    record.agreement_id = None
    record.consent_token = consent_token
    return record


def _make_orphaned_consent(consent_token: object) -> MagicMock:
    """Create an orphaned SMS consent record (customer_id=None)."""
    record = MagicMock()
    record.id = uuid4()
    record.customer_id = None
    record.consent_token = consent_token
    return record


def _mock_session(
    disclosures: list[MagicMock],
    consents: list[MagicMock],
) -> AsyncMock:
    """Create a mock session returning given orphaned records."""
    session = AsyncMock()
    disc_result = MagicMock()
    disc_result.scalars.return_value.all.return_value = disclosures
    consent_result = MagicMock()
    consent_result.scalars.return_value.all.return_value = consents
    session.execute = AsyncMock(side_effect=[disc_result, consent_result])
    session.flush = AsyncMock()
    return session


@pytest.mark.unit
@pytest.mark.asyncio
class TestConsentTokenLinkageProperty:
    """Property-based tests for consent token linkage."""

    @given(
        token=consent_tokens,
        cust_id=customer_ids,
        agr_id=agreement_ids,
        disc_count=orphan_counts,
        consent_count=orphan_counts,
    )
    @settings(max_examples=30)
    async def test_orphaned_records_linked_to_customer_and_agreement(
        self,
        token: object,
        cust_id: object,
        agr_id: object,
        disc_count: int,
        consent_count: int,
    ) -> None:
        """Property: all orphaned records with matching consent_token are linked.

        After link_orphaned_records, every orphaned disclosure has
        customer_id and agreement_id set, and every orphaned consent
        has customer_id set.
        """
        disclosures = [_make_orphaned_disclosure(token) for _ in range(disc_count)]
        consents = [_make_orphaned_consent(token) for _ in range(consent_count)]
        session = _mock_session(disclosures, consents)
        svc = ComplianceService(session)

        result = await svc.link_orphaned_records(token, cust_id, agr_id)  # type: ignore[arg-type]

        assert result["disclosures_linked"] == disc_count
        assert result["consents_linked"] == consent_count

        for d in disclosures:
            assert d.customer_id == cust_id
            assert d.agreement_id == agr_id

        for c in consents:
            assert c.customer_id == cust_id

    @given(
        token=consent_tokens,
        cust_id=customer_ids,
        agr_id=agreement_ids,
    )
    @settings(max_examples=30)
    async def test_no_orphans_yields_zero_linkages(
        self,
        token: object,
        cust_id: object,
        agr_id: object,
    ) -> None:
        """Property: when no orphaned records exist, zero linkages reported."""
        session = _mock_session([], [])
        svc = ComplianceService(session)

        result = await svc.link_orphaned_records(token, cust_id, agr_id)  # type: ignore[arg-type]

        assert result["disclosures_linked"] == 0
        assert result["consents_linked"] == 0

    @given(
        token=consent_tokens,
        cust_id=customer_ids,
        agr_id=agreement_ids,
        disc_count=orphan_counts,
    )
    @settings(max_examples=30)
    async def test_disclosures_only_linked(
        self,
        token: object,
        cust_id: object,
        agr_id: object,
        disc_count: int,
    ) -> None:
        """Property: orphaned disclosures linked even when no consent records exist."""
        disclosures = [_make_orphaned_disclosure(token) for _ in range(disc_count)]
        session = _mock_session(disclosures, [])
        svc = ComplianceService(session)

        result = await svc.link_orphaned_records(token, cust_id, agr_id)  # type: ignore[arg-type]

        assert result["disclosures_linked"] == disc_count
        assert result["consents_linked"] == 0
        for d in disclosures:
            assert d.customer_id == cust_id
            assert d.agreement_id == agr_id

    @given(
        token=consent_tokens,
        cust_id=customer_ids,
        agr_id=agreement_ids,
        consent_count=orphan_counts,
    )
    @settings(max_examples=30)
    async def test_consents_only_linked(
        self,
        token: object,
        cust_id: object,
        agr_id: object,
        consent_count: int,
    ) -> None:
        """Property: orphaned consents linked even when no disclosure records exist."""
        consents = [_make_orphaned_consent(token) for _ in range(consent_count)]
        session = _mock_session([], consents)
        svc = ComplianceService(session)

        result = await svc.link_orphaned_records(token, cust_id, agr_id)  # type: ignore[arg-type]

        assert result["disclosures_linked"] == 0
        assert result["consents_linked"] == consent_count
        for c in consents:
            assert c.customer_id == cust_id
