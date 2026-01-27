"""Tests for AI and SMS schemas.

Validates: AI Assistant Requirements 15.1-15.10
"""

from datetime import date, datetime, time
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.schemas.ai import (
    AIActionType,
    AIAuditLogEntry,
    AIChatRequest,
    AIChatResponse,
    AIDecisionRequest,
    AIEntityType,
    AIUsageResponse,
    CommunicationDraft,
    CommunicationDraftRequest,
    DeliveryStatus,
    EstimateBreakdown,
    EstimateGenerateRequest,
    JobCategorization,
    JobCategorizationRequest,
    MessageType,
    ScheduledJob,
    ScheduleGenerateRequest,
    ScheduleSummary,
    ScheduleWarning,
    SimilarJob,
    StaffAssignment,
    UserDecision,
)
from grins_platform.schemas.sms import (
    CommunicationsQueueItem,
    CommunicationsQueueResponse,
    SMSSendRequest,
    SMSSendResponse,
    SMSWebhookPayload,
)


class TestAIEnums:
    """Tests for AI enum types."""

    def test_ai_action_type_values(self) -> None:
        """Test AIActionType enum values."""
        assert AIActionType.SCHEDULE_GENERATION.value == "schedule_generation"
        assert AIActionType.JOB_CATEGORIZATION.value == "job_categorization"
        assert AIActionType.COMMUNICATION_DRAFT.value == "communication_draft"
        assert AIActionType.ESTIMATE_GENERATION.value == "estimate_generation"
        assert AIActionType.BUSINESS_QUERY.value == "business_query"

    def test_ai_entity_type_values(self) -> None:
        """Test AIEntityType enum values."""
        assert AIEntityType.JOB.value == "job"
        assert AIEntityType.CUSTOMER.value == "customer"
        assert AIEntityType.APPOINTMENT.value == "appointment"
        assert AIEntityType.SCHEDULE.value == "schedule"

    def test_user_decision_values(self) -> None:
        """Test UserDecision enum values."""
        assert UserDecision.APPROVED.value == "approved"
        assert UserDecision.REJECTED.value == "rejected"
        assert UserDecision.MODIFIED.value == "modified"
        assert UserDecision.PENDING.value == "pending"

    def test_message_type_values(self) -> None:
        """Test MessageType enum values."""
        assert MessageType.APPOINTMENT_CONFIRMATION.value == "appointment_confirmation"
        assert MessageType.APPOINTMENT_REMINDER.value == "appointment_reminder"
        assert MessageType.ON_THE_WAY.value == "on_the_way"
        assert MessageType.INVOICE.value == "invoice"

    def test_delivery_status_values(self) -> None:
        """Test DeliveryStatus enum values."""
        assert DeliveryStatus.PENDING.value == "pending"
        assert DeliveryStatus.SENT.value == "sent"
        assert DeliveryStatus.DELIVERED.value == "delivered"
        assert DeliveryStatus.FAILED.value == "failed"


class TestChatSchemas:
    """Tests for chat request/response schemas."""

    def test_chat_request_valid(self) -> None:
        """Test valid chat request."""
        request = AIChatRequest(message="How many jobs today?")
        assert request.message == "How many jobs today?"
        assert request.session_id is None

    def test_chat_request_with_session(self) -> None:
        """Test chat request with session ID."""
        session_id = uuid4()
        request = AIChatRequest(message="Follow up", session_id=session_id)
        assert request.session_id == session_id

    def test_chat_request_empty_message_fails(self) -> None:
        """Test that empty message fails validation."""
        with pytest.raises(ValidationError):
            AIChatRequest(message="")

    def test_chat_response_valid(self) -> None:
        """Test valid chat response."""
        response = AIChatResponse(
            message="You have 5 jobs today.",
            session_id=uuid4(),
            tokens_used=150,
        )
        assert response.tokens_used == 150
        assert response.is_streaming is False


class TestScheduleSchemas:
    """Tests for schedule generation schemas."""

    def test_scheduled_job_valid(self) -> None:
        """Test valid scheduled job."""
        job = ScheduledJob(
            job_id=uuid4(),
            customer_name="John Doe",
            address="123 Main St",
            job_type="spring_startup",
            estimated_duration_minutes=45,
            time_window_start=time(9, 0),
            time_window_end=time(11, 0),
        )
        assert job.estimated_duration_minutes == 45

    def test_staff_assignment_valid(self) -> None:
        """Test valid staff assignment."""
        assignment = StaffAssignment(
            staff_id=uuid4(),
            staff_name="Viktor",
            jobs=[],
            total_jobs=0,
            total_minutes=0,
        )
        assert assignment.staff_name == "Viktor"

    def test_schedule_warning_valid(self) -> None:
        """Test valid schedule warning."""
        warning = ScheduleWarning(
            warning_type="equipment_conflict",
            message="Compressor needed for multiple jobs",
        )
        assert warning.warning_type == "equipment_conflict"

    def test_schedule_generate_request_valid(self) -> None:
        """Test valid schedule generate request."""
        request = ScheduleGenerateRequest(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 7),
        )
        assert request.include_pending_jobs is True

    def test_schedule_summary_valid(self) -> None:
        """Test valid schedule summary."""
        summary = ScheduleSummary(
            total_jobs=25,
            total_staff=3,
            total_days=5,
            jobs_per_day_avg=5.0,
            warnings_count=2,
        )
        assert summary.jobs_per_day_avg == 5.0


class TestCategorizationSchemas:
    """Tests for job categorization schemas."""

    def test_job_categorization_valid(self) -> None:
        """Test valid job categorization."""
        cat = JobCategorization(
            job_id=uuid4(),
            suggested_category="ready_to_schedule",
            suggested_job_type="spring_startup",
            confidence_score=0.95,
            requires_review=False,
        )
        assert cat.confidence_score == 0.95

    def test_job_categorization_confidence_bounds(self) -> None:
        """Test confidence score bounds."""
        with pytest.raises(ValidationError):
            JobCategorization(
                job_id=uuid4(),
                suggested_category="ready_to_schedule",
                suggested_job_type="spring_startup",
                confidence_score=1.5,  # Invalid: > 1
                requires_review=False,
            )

    def test_categorization_request_valid(self) -> None:
        """Test valid categorization request."""
        request = JobCategorizationRequest()
        assert request.include_uncategorized_only is True


class TestCommunicationSchemas:
    """Tests for communication draft schemas."""

    def test_communication_draft_valid(self) -> None:
        """Test valid communication draft."""
        draft = CommunicationDraft(
            draft_id=uuid4(),
            customer_id=uuid4(),
            customer_name="John Doe",
            customer_phone="6125551234",
            message_type=MessageType.APPOINTMENT_CONFIRMATION,
            message_content="Your appointment is confirmed for tomorrow.",
        )
        assert draft.is_slow_payer is False

    def test_communication_draft_request_valid(self) -> None:
        """Test valid communication draft request."""
        request = CommunicationDraftRequest(
            customer_id=uuid4(),
            message_type=MessageType.APPOINTMENT_REMINDER,
        )
        assert request.job_id is None


class TestEstimateSchemas:
    """Tests for estimate generation schemas."""

    def test_similar_job_valid(self) -> None:
        """Test valid similar job."""
        job = SimilarJob(
            job_id=uuid4(),
            job_type="installation",
            zone_count=8,
            final_amount=Decimal("5600.00"),
            completed_at=datetime.now(),
        )
        assert job.zone_count == 8

    def test_estimate_breakdown_valid(self) -> None:
        """Test valid estimate breakdown."""
        breakdown = EstimateBreakdown(
            materials=Decimal("1500.00"),
            labor=Decimal("2000.00"),
            equipment=Decimal("500.00"),
            margin=Decimal("800.00"),
            total=Decimal("4800.00"),
        )
        assert breakdown.total == Decimal("4800.00")

    def test_estimate_generate_request_valid(self) -> None:
        """Test valid estimate generate request."""
        request = EstimateGenerateRequest(
            job_id=uuid4(),
            zone_count=6,
        )
        assert request.include_similar_jobs is True


class TestAuditSchemas:
    """Tests for audit log schemas."""

    def test_ai_usage_response_valid(self) -> None:
        """Test valid AI usage response."""
        response = AIUsageResponse(
            user_id=uuid4(),
            usage_date=date.today(),
            request_count=50,
            total_input_tokens=10000,
            total_output_tokens=5000,
            estimated_cost_usd=0.15,
            remaining_requests=50,
        )
        assert response.daily_limit == 100

    def test_ai_audit_log_entry_valid(self) -> None:
        """Test valid audit log entry."""
        entry = AIAuditLogEntry(
            id=uuid4(),
            action_type=AIActionType.SCHEDULE_GENERATION,
            entity_type=AIEntityType.SCHEDULE,
            entity_id=None,
            ai_recommendation={"schedule": []},
            confidence_score=0.9,
            user_decision=UserDecision.APPROVED,
            decision_at=datetime.now(),
            request_tokens=500,
            response_tokens=1000,
            estimated_cost_usd=0.02,
            created_at=datetime.now(),
        )
        assert entry.action_type == AIActionType.SCHEDULE_GENERATION

    def test_ai_decision_request_valid(self) -> None:
        """Test valid AI decision request."""
        request = AIDecisionRequest(
            decision=UserDecision.APPROVED,
        )
        assert request.modified_data is None


class TestSMSSchemas:
    """Tests for SMS schemas."""

    def test_sms_send_request_valid(self) -> None:
        """Test valid SMS send request."""
        request = SMSSendRequest(
            customer_id=uuid4(),
            phone="6125551234",
            message="Your appointment is confirmed.",
            message_type=MessageType.APPOINTMENT_CONFIRMATION,
        )
        assert request.job_id is None

    def test_sms_send_request_message_too_long(self) -> None:
        """Test SMS message length validation."""
        with pytest.raises(ValidationError):
            SMSSendRequest(
                customer_id=uuid4(),
                phone="6125551234",
                message="x" * 1601,  # Too long
                message_type=MessageType.CUSTOM,
            )

    def test_sms_send_response_valid(self) -> None:
        """Test valid SMS send response."""
        response = SMSSendResponse(
            success=True,
            message_id=uuid4(),
            twilio_sid="SM123456",
            status="sent",
        )
        assert response.twilio_sid == "SM123456"

    def test_sms_webhook_payload_valid(self) -> None:
        """Test valid SMS webhook payload."""
        payload = SMSWebhookPayload(
            MessageSid="SM123456",
            MessageStatus="delivered",
            To="+16125551234",
            From="+16125559999",
        )
        assert payload.message_sid == "SM123456"

    def test_communications_queue_item_valid(self) -> None:
        """Test valid communications queue item."""
        item = CommunicationsQueueItem(
            id=str(uuid4()),
            customer_id=str(uuid4()),
            message_type="appointment_reminder",
            message_content="Reminder: Your appointment is tomorrow.",
            recipient_phone="6125551234",
            delivery_status="pending",
            scheduled_for=None,
            created_at=datetime.now(),
        )
        assert item.delivery_status == "pending"

    def test_communications_queue_response_valid(self) -> None:
        """Test valid communications queue response."""
        response = CommunicationsQueueResponse(
            items=[],
            total=0,
            limit=20,
            offset=0,
        )
        assert response.total == 0
