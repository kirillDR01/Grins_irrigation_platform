"""Property tests for audit logging.

Property 4: Audit Completeness
- Every AI recommendation is logged
- Every user decision is recorded

Validates: Requirements 2.7, 2.8, 7.8, 7.9, 7.10
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.schemas.ai import AIActionType, AIEntityType, UserDecision
from grins_platform.services.ai.audit import AuditService


@pytest.mark.asyncio
class TestAuditProperty:
    """Property-based tests for audit logging."""

    @given(
        action_type=st.sampled_from(list(AIActionType)),
        entity_type=st.sampled_from(list(AIEntityType)),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=20)
    async def test_all_recommendations_logged(
        self,
        action_type: AIActionType,
        entity_type: AIEntityType,
        confidence: float,
    ) -> None:
        """Property: All AI recommendations are logged."""
        mock_session = AsyncMock()
        service = AuditService(mock_session)

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        service.audit_repo.create = AsyncMock(return_value=mock_audit)

        result = await service.log_recommendation(
            action_type=action_type,
            entity_type=entity_type,
            ai_recommendation={"test": "data"},
            confidence_score=confidence,
        )

        assert result is not None
        service.audit_repo.create.assert_called_once()

    @given(decision=st.sampled_from(list(UserDecision)))
    @settings(max_examples=10)
    async def test_all_decisions_recorded(self, decision: UserDecision) -> None:
        """Property: All user decisions are recorded."""
        mock_session = AsyncMock()
        service = AuditService(mock_session)

        mock_audit = MagicMock()
        mock_audit.id = uuid4()
        mock_audit.user_decision = decision.value
        service.audit_repo.update_decision = AsyncMock(return_value=mock_audit)

        audit_id = uuid4()
        user_id = uuid4()

        result = await service.record_decision(audit_id, decision, user_id)

        assert result is not None
        service.audit_repo.update_decision.assert_called_once_with(
            audit_id,
            decision,
            user_id,
        )

    async def test_decision_not_found_returns_none(self) -> None:
        """Test that recording decision for non-existent audit returns None."""
        mock_session = AsyncMock()
        service = AuditService(mock_session)
        service.audit_repo.update_decision = AsyncMock(return_value=None)

        result = await service.record_decision(
            uuid4(),
            UserDecision.APPROVED,
            uuid4(),
        )

        assert result is None
