"""Tests for AI repositories.

Validates: AI Assistant Requirements 2.1, 2.7, 2.8, 3.1, 3.2, 3.7, 7.8, 7.9, 7.10
"""

from datetime import date, datetime, timedelta
from uuid import uuid4

import pytest

from grins_platform.repositories.ai_audit_log_repository import AIAuditLogRepository
from grins_platform.repositories.ai_usage_repository import AIUsageRepository
from grins_platform.repositories.sent_message_repository import SentMessageRepository
from grins_platform.schemas.ai import (
    AIActionType,
    AIEntityType,
    DeliveryStatus,
    MessageType,
    UserDecision,
)


@pytest.mark.asyncio
class TestAIAuditLogRepository:
    """Tests for AIAuditLogRepository."""

    async def test_create_audit_log(self, async_session) -> None:
        """Test creating an audit log entry."""
        repo = AIAuditLogRepository(async_session)

        audit_log = await repo.create(
            action_type=AIActionType.SCHEDULE_GENERATION,
            entity_type=AIEntityType.SCHEDULE,
            ai_recommendation={"schedule": [], "summary": "test"},
            confidence_score=0.95,
        )

        assert audit_log.id is not None
        assert audit_log.action_type == "schedule_generation"
        assert audit_log.entity_type == "schedule"
        assert audit_log.confidence_score == 0.95

    async def test_get_by_id(self, async_session) -> None:
        """Test getting audit log by ID."""
        repo = AIAuditLogRepository(async_session)

        created = await repo.create(
            action_type=AIActionType.JOB_CATEGORIZATION,
            entity_type=AIEntityType.JOB,
            ai_recommendation={"category": "ready_to_schedule"},
        )

        fetched = await repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    async def test_get_by_id_not_found(self, async_session) -> None:
        """Test getting non-existent audit log."""
        repo = AIAuditLogRepository(async_session)
        result = await repo.get_by_id(uuid4())
        assert result is None

    async def test_update_decision(self, async_session) -> None:
        """Test updating user decision."""
        repo = AIAuditLogRepository(async_session)
        user_id = uuid4()

        audit_log = await repo.create(
            action_type=AIActionType.COMMUNICATION_DRAFT,
            entity_type=AIEntityType.COMMUNICATION,
            ai_recommendation={"message": "test"},
        )

        updated = await repo.update_decision(
            audit_log.id,
            UserDecision.APPROVED,
            user_id,
        )

        assert updated is not None
        assert updated.user_decision == "approved"
        assert updated.user_id == user_id
        assert updated.decision_at is not None

    async def test_list_with_filters(self, async_session) -> None:
        """Test listing with filters."""
        repo = AIAuditLogRepository(async_session)

        await repo.create(
            action_type=AIActionType.SCHEDULE_GENERATION,
            entity_type=AIEntityType.SCHEDULE,
            ai_recommendation={},
        )
        await repo.create(
            action_type=AIActionType.JOB_CATEGORIZATION,
            entity_type=AIEntityType.JOB,
            ai_recommendation={},
        )

        results, _total = await repo.list_with_filters(
            action_type=AIActionType.SCHEDULE_GENERATION,
        )

        assert len(results) >= 1
        assert all(r.action_type == "schedule_generation" for r in results)


@pytest.mark.asyncio
class TestAIUsageRepository:
    """Tests for AIUsageRepository."""

    async def test_get_or_create_new(self, async_session) -> None:
        """Test creating new usage record."""
        repo = AIUsageRepository(async_session)
        user_id = uuid4()

        usage = await repo.get_or_create(user_id, date.today())

        assert usage.id is not None
        assert usage.user_id == user_id
        assert usage.request_count == 0

    async def test_get_or_create_existing(self, async_session) -> None:
        """Test getting existing usage record."""
        repo = AIUsageRepository(async_session)
        user_id = uuid4()
        today = date.today()

        first = await repo.get_or_create(user_id, today)
        second = await repo.get_or_create(user_id, today)

        assert first.id == second.id

    async def test_increment(self, async_session) -> None:
        """Test incrementing usage counters."""
        repo = AIUsageRepository(async_session)
        user_id = uuid4()

        usage = await repo.increment(
            user_id,
            date.today(),
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.01,
        )

        assert usage.request_count == 1
        assert usage.total_input_tokens == 100
        assert usage.total_output_tokens == 50

    async def test_get_daily_usage(self, async_session) -> None:
        """Test getting daily usage."""
        repo = AIUsageRepository(async_session)
        user_id = uuid4()
        today = date.today()

        await repo.increment(user_id, today, input_tokens=50)

        usage = await repo.get_daily_usage(user_id, today)
        assert usage is not None
        assert usage.total_input_tokens == 50


@pytest.mark.asyncio
class TestSentMessageRepository:
    """Tests for SentMessageRepository."""

    async def test_create_message(self, async_session) -> None:
        """Test creating a message."""
        repo = SentMessageRepository(async_session)
        customer_id = uuid4()

        message = await repo.create(
            customer_id=customer_id,
            message_type=MessageType.APPOINTMENT_CONFIRMATION,
            message_content="Your appointment is confirmed.",
            recipient_phone="+16125551234",
        )

        assert message.id is not None
        assert message.customer_id == customer_id
        assert message.delivery_status == "pending"

    async def test_create_scheduled_message(self, async_session) -> None:
        """Test creating a scheduled message."""
        repo = SentMessageRepository(async_session)
        scheduled_time = datetime.now() + timedelta(hours=1)

        message = await repo.create(
            customer_id=uuid4(),
            message_type=MessageType.APPOINTMENT_REMINDER,
            message_content="Reminder",
            recipient_phone="+16125551234",
            scheduled_for=scheduled_time,
        )

        assert message.delivery_status == "scheduled"
        assert message.scheduled_for == scheduled_time

    async def test_update_message(self, async_session) -> None:
        """Test updating a message."""
        repo = SentMessageRepository(async_session)

        message = await repo.create(
            customer_id=uuid4(),
            message_type=MessageType.CUSTOM,
            message_content="Test",
            recipient_phone="+16125551234",
        )

        updated = await repo.update(
            message.id,
            delivery_status=DeliveryStatus.SENT,
            twilio_sid="SM123456",
            sent_at=datetime.now(),
        )

        assert updated is not None
        assert updated.delivery_status == "sent"
        assert updated.twilio_sid == "SM123456"

    async def test_get_by_customer_and_type(self, async_session) -> None:
        """Test getting messages by customer and type."""
        repo = SentMessageRepository(async_session)
        customer_id = uuid4()

        await repo.create(
            customer_id=customer_id,
            message_type=MessageType.APPOINTMENT_CONFIRMATION,
            message_content="Test 1",
            recipient_phone="+16125551234",
        )

        messages = await repo.get_by_customer_and_type(
            customer_id,
            MessageType.APPOINTMENT_CONFIRMATION,
        )

        assert len(messages) >= 1

    async def test_delete_pending_message(self, async_session) -> None:
        """Test deleting a pending message."""
        repo = SentMessageRepository(async_session)

        message = await repo.create(
            customer_id=uuid4(),
            message_type=MessageType.CUSTOM,
            message_content="Test",
            recipient_phone="+16125551234",
        )

        result = await repo.delete(message.id)
        assert result is True

        fetched = await repo.get_by_id(message.id)
        assert fetched is None
