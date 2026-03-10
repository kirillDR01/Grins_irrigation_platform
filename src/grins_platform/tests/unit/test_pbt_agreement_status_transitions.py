"""Property test for agreement status transition validity.

Property 4: Status Transition Validity
For any (current_status, target_status) pair, accept iff target is in valid
transitions map; all invalid rejected with descriptive error; every accepted
transition produces AgreementStatusLog.

Validates: Requirements 5.1, 5.2, 3.2
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.exceptions import InvalidAgreementStatusTransitionError
from grins_platform.models.enums import (
    VALID_AGREEMENT_STATUS_TRANSITIONS,
    AgreementStatus,
)
from grins_platform.services.agreement_service import AgreementService

agreement_statuses = st.sampled_from(list(AgreementStatus))


def _make_agreement(status: AgreementStatus) -> MagicMock:
    agr = MagicMock()
    agr.id = MagicMock()
    agr.status = status.value
    agr.agreement_number = "AGR-2026-001"
    return agr


def _make_service(agreement: MagicMock) -> AgreementService:
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=agreement)
    repo.update = AsyncMock(return_value=agreement)
    return AgreementService(
        agreement_repo=repo,
        tier_repo=AsyncMock(),
        stripe_settings=MagicMock(is_configured=False),
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestStatusTransitionValidityProperty:
    """Property-based tests for status transition validity."""

    @given(current=agreement_statuses, target=agreement_statuses)
    @settings(max_examples=50)
    async def test_valid_transitions_accepted_invalid_rejected(
        self,
        current: AgreementStatus,
        target: AgreementStatus,
    ) -> None:
        """Accepted iff target in VALID_AGREEMENT_STATUS_TRANSITIONS."""
        agr = _make_agreement(current)
        svc = _make_service(agr)
        valid_targets = VALID_AGREEMENT_STATUS_TRANSITIONS.get(current, set())

        if target in valid_targets:
            result = await svc.transition_status(agr.id, target)
            assert result is not None
        else:
            with pytest.raises(InvalidAgreementStatusTransitionError) as exc_info:
                await svc.transition_status(agr.id, target)
            assert current.value in str(exc_info.value)
            assert target.value in str(exc_info.value)

    @given(current=agreement_statuses, target=agreement_statuses)
    @settings(max_examples=50)
    async def test_accepted_transition_produces_status_log(
        self,
        current: AgreementStatus,
        target: AgreementStatus,
    ) -> None:
        """Every accepted transition creates an AgreementStatusLog entry."""
        valid_targets = VALID_AGREEMENT_STATUS_TRANSITIONS.get(current, set())
        if target not in valid_targets:
            return  # skip invalid pairs

        agr = _make_agreement(current)
        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=agr)
        repo.update = AsyncMock(return_value=agr)
        svc = AgreementService(
            agreement_repo=repo,
            tier_repo=AsyncMock(),
            stripe_settings=MagicMock(is_configured=False),
        )

        await svc.transition_status(agr.id, target)

        repo.add_status_log.assert_called_once()
        log_kwargs = repo.add_status_log.call_args.kwargs
        assert log_kwargs["old_status"] == current.value
        assert log_kwargs["new_status"] == target.value
