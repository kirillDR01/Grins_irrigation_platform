"""Property test for compliance disclosure completeness.

Property 8: Compliance Disclosure Completeness
For any ACTIVE agreement through full lifecycle: PRE_SALE + CONFIRMATION exist;
PENDING_RENEWAL → RENEWAL_NOTICE exists; CANCELLED → CANCELLATION_CONF exists.

Validates: Requirements 34.1, 34.3, 35.1, 36.1
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.models.enums import AgreementStatus, DisclosureType
from grins_platform.services.compliance_service import ComplianceService

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

agreement_ids = st.uuids()
# Subset of statuses representing lifecycle stages
lifecycle_statuses = st.sampled_from(list(AgreementStatus))
# Whether the agreement has ever been in PENDING_RENEWAL
has_been_pending_renewal = st.booleans()
# Which disclosure types are recorded
disclosure_subsets = st.frozensets(
    st.sampled_from([d.value for d in DisclosureType]),
    min_size=0,
    max_size=len(DisclosureType),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_status_log(new_status: str) -> MagicMock:
    log = MagicMock()
    log.new_status = new_status
    return log


def _mock_session(
    agreement: MagicMock | None,
    recorded_types: frozenset[str],
) -> AsyncMock:
    """Mock session returning agreement and recorded disclosure types."""
    session = AsyncMock()

    agr_result = MagicMock()
    agr_result.scalar_one_or_none.return_value = agreement

    disc_result = MagicMock()
    disc_result.all.return_value = [(t,) for t in recorded_types]

    session.execute = AsyncMock(side_effect=[agr_result, disc_result])
    return session


def _build_agreement(
    agr_id: UUID,
    status: AgreementStatus,
    ever_pending_renewal: bool,
) -> MagicMock:
    agr = MagicMock()
    agr.id = agr_id
    agr.status = status.value
    logs: list[MagicMock] = []
    if ever_pending_renewal and status != AgreementStatus.PENDING_RENEWAL:
        logs.append(_make_status_log(AgreementStatus.PENDING_RENEWAL.value))
    agr.status_logs = logs
    return agr


def _expected_required(
    status: AgreementStatus,
    ever_pending_renewal: bool,
) -> list[str]:
    """Compute expected required disclosures for a given state."""
    required = [DisclosureType.PRE_SALE.value, DisclosureType.CONFIRMATION.value]
    if status == AgreementStatus.PENDING_RENEWAL or ever_pending_renewal:
        required.append(DisclosureType.RENEWAL_NOTICE.value)
    if status == AgreementStatus.CANCELLED:
        required.append(DisclosureType.CANCELLATION_CONF.value)
    return required


# ---------------------------------------------------------------------------
# Property tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
class TestComplianceDisclosureCompletenessProperty:
    """Property 8: Compliance Disclosure Completeness."""

    @given(
        agr_id=agreement_ids,
        status=lifecycle_statuses,
        ever_pr=has_been_pending_renewal,
        recorded=disclosure_subsets,
    )
    @settings(max_examples=50)
    async def test_required_disclosures_match_lifecycle(
        self,
        agr_id: UUID,
        status: AgreementStatus,
        ever_pr: bool,
        recorded: frozenset[str],
    ) -> None:
        """Required disclosures determined by status and history."""
        agreement = _build_agreement(agr_id, status, ever_pr)
        session = _mock_session(agreement, recorded)
        svc = ComplianceService(session)

        result = await svc.get_compliance_status(agr_id)

        expected_req = _expected_required(status, ever_pr)
        assert set(result.recorded) | set(result.missing) == set(expected_req)
        assert set(result.recorded) == set(expected_req) & set(recorded)
        assert set(result.missing) == set(expected_req) - set(recorded)

    @given(
        agr_id=agreement_ids,
        status=lifecycle_statuses,
        ever_pr=has_been_pending_renewal,
    )
    @settings(max_examples=30)
    async def test_all_recorded_yields_no_missing(
        self,
        agr_id: UUID,
        status: AgreementStatus,
        ever_pr: bool,
    ) -> None:
        """When all required disclosures are recorded, missing is empty."""
        expected_req = _expected_required(status, ever_pr)
        agreement = _build_agreement(agr_id, status, ever_pr)
        session = _mock_session(agreement, frozenset(expected_req))
        svc = ComplianceService(session)

        result = await svc.get_compliance_status(agr_id)

        assert result.missing == []
        assert set(result.recorded) == set(expected_req)

    @given(
        agr_id=agreement_ids,
        status=lifecycle_statuses,
        ever_pr=has_been_pending_renewal,
    )
    @settings(max_examples=30)
    async def test_none_recorded_yields_all_missing(
        self,
        agr_id: UUID,
        status: AgreementStatus,
        ever_pr: bool,
    ) -> None:
        """When no disclosures are recorded, all required are missing."""
        agreement = _build_agreement(agr_id, status, ever_pr)
        session = _mock_session(agreement, frozenset())
        svc = ComplianceService(session)

        result = await svc.get_compliance_status(agr_id)

        expected_req = _expected_required(status, ever_pr)
        assert result.recorded == []
        assert set(result.missing) == set(expected_req)

    @given(agr_id=agreement_ids)
    @settings(max_examples=20)
    async def test_pre_sale_and_confirmation_always_required(
        self,
        agr_id: UUID,
    ) -> None:
        """PRE_SALE and CONFIRMATION are required for every agreement."""
        agreement = _build_agreement(agr_id, AgreementStatus.ACTIVE, False)
        session = _mock_session(agreement, frozenset())
        svc = ComplianceService(session)

        result = await svc.get_compliance_status(agr_id)

        assert DisclosureType.PRE_SALE.value in result.missing
        assert DisclosureType.CONFIRMATION.value in result.missing

    @given(agr_id=agreement_ids, ever_pr=has_been_pending_renewal)
    @settings(max_examples=20)
    async def test_pending_renewal_requires_renewal_notice(
        self,
        agr_id: UUID,
        ever_pr: bool,
    ) -> None:
        """PENDING_RENEWAL status (current or historical) requires RENEWAL_NOTICE."""
        agreement = _build_agreement(agr_id, AgreementStatus.PENDING_RENEWAL, ever_pr)
        session = _mock_session(agreement, frozenset())
        svc = ComplianceService(session)

        result = await svc.get_compliance_status(agr_id)

        assert DisclosureType.RENEWAL_NOTICE.value in result.missing

    @given(agr_id=agreement_ids)
    @settings(max_examples=20)
    async def test_cancelled_requires_cancellation_conf(
        self,
        agr_id: UUID,
    ) -> None:
        """CANCELLED status requires CANCELLATION_CONF disclosure."""
        agreement = _build_agreement(agr_id, AgreementStatus.CANCELLED, False)
        session = _mock_session(agreement, frozenset())
        svc = ComplianceService(session)

        result = await svc.get_compliance_status(agr_id)

        assert DisclosureType.CANCELLATION_CONF.value in result.missing

    @given(agr_id=agreement_ids)
    @settings(max_examples=20)
    async def test_historical_pending_renewal_still_requires_notice(
        self,
        agr_id: UUID,
    ) -> None:
        """Historical PENDING_RENEWAL still needs RENEWAL_NOTICE."""
        agreement = _build_agreement(agr_id, AgreementStatus.ACTIVE, True)
        session = _mock_session(agreement, frozenset())
        svc = ComplianceService(session)

        result = await svc.get_compliance_status(agr_id)

        assert DisclosureType.RENEWAL_NOTICE.value in result.missing
