"""Functional tests for estimate and portal operations.

Tests estimate creation, template-based creation, portal approval/rejection,
follow-up lifecycle, and lead tag updates with mocked repositories and
external services.

Validates: Requirements 16.9, 17.8, 51.8
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from grins_platform.exceptions import (
    EstimateAlreadyApprovedError,
    EstimateNotFoundError,
    EstimateTemplateNotFoundError,
    EstimateTokenExpiredError,
)
from grins_platform.models.enums import (
    ActionTag,
    EstimateStatus,
    FollowUpStatus,
)
from grins_platform.schemas.estimate import EstimateCreate
from grins_platform.services.estimate_service import (
    FOLLOW_UP_DAYS,
    TOKEN_VALIDITY_DAYS,
    EstimateService,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_estimate(**overrides: Any) -> MagicMock:
    """Create a mock Estimate with all fields."""
    est = MagicMock()
    est.id = overrides.get("id", uuid4())
    est.lead_id = overrides.get("lead_id")
    est.customer_id = overrides.get("customer_id")
    est.job_id = overrides.get("job_id")
    est.template_id = overrides.get("template_id")
    est.status = overrides.get("status", EstimateStatus.DRAFT.value)
    est.line_items = overrides.get(
        "line_items",
        [
            {"item": "Sprinkler Head", "unit_price": "25.00", "quantity": "4"},
        ],
    )
    est.options = overrides.get("options")
    est.subtotal = overrides.get("subtotal", Decimal("100.00"))
    est.tax_amount = overrides.get("tax_amount", Decimal("8.25"))
    est.discount_amount = overrides.get("discount_amount", Decimal(0))
    est.total = overrides.get("total", Decimal("108.25"))
    est.promotion_code = overrides.get("promotion_code")
    est.valid_until = overrides.get(
        "valid_until",
        datetime.now(tz=timezone.utc) + timedelta(days=30),
    )
    est.notes = overrides.get("notes")
    est.customer_token = overrides.get("customer_token", uuid4())
    est.token_expires_at = overrides.get(
        "token_expires_at",
        datetime.now(tz=timezone.utc) + timedelta(days=TOKEN_VALIDITY_DAYS),
    )
    est.token_readonly = overrides.get("token_readonly", False)
    est.approved_at = overrides.get("approved_at")
    est.approved_ip = overrides.get("approved_ip")
    est.approved_user_agent = overrides.get("approved_user_agent")
    est.rejected_at = overrides.get("rejected_at")
    est.rejection_reason = overrides.get("rejection_reason")
    est.created_at = overrides.get(
        "created_at",
        datetime.now(tz=timezone.utc),
    )
    est.updated_at = datetime.now(tz=timezone.utc)

    # Related objects
    customer = overrides.get("customer")
    est.customer = customer
    lead = overrides.get("lead")
    est.lead = lead

    return est


def _make_template(**overrides: Any) -> MagicMock:
    """Create a mock EstimateTemplate."""
    tpl = MagicMock()
    tpl.id = overrides.get("id", uuid4())
    tpl.name = overrides.get("name", "Standard Irrigation Install")
    tpl.description = overrides.get("description", "Full system install")
    tpl.line_items = overrides.get(
        "line_items",
        [
            {"item": "Controller", "unit_price": "150.00", "quantity": "1"},
            {"item": "Valve", "unit_price": "45.00", "quantity": "6"},
            {"item": "Sprinkler Head", "unit_price": "12.00", "quantity": "20"},
        ],
    )
    tpl.terms = overrides.get("terms", "Net 30")
    tpl.is_active = overrides.get("is_active", True)
    tpl.created_at = datetime.now(tz=timezone.utc)
    tpl.updated_at = datetime.now(tz=timezone.utc)
    return tpl


def _make_follow_up(**overrides: Any) -> MagicMock:
    """Create a mock EstimateFollowUp."""
    fu = MagicMock()
    fu.id = overrides.get("id", uuid4())
    fu.estimate_id = overrides.get("estimate_id", uuid4())
    fu.follow_up_number = overrides.get("follow_up_number", 1)
    fu.scheduled_at = overrides.get(
        "scheduled_at",
        datetime.now(tz=timezone.utc) - timedelta(hours=1),
    )
    fu.sent_at = overrides.get("sent_at")
    fu.channel = overrides.get("channel", "sms")
    fu.message = overrides.get("message")
    fu.promotion_code = overrides.get("promotion_code")
    fu.status = overrides.get("status", FollowUpStatus.SCHEDULED.value)
    return fu


def _make_customer(**overrides: Any) -> MagicMock:
    """Create a mock Customer for estimate relations."""
    c = MagicMock()
    c.id = overrides.get("id", uuid4())
    c.phone = overrides.get("phone", "5125551234")
    c.email = overrides.get("email", "customer@example.com")
    c.first_name = overrides.get("first_name", "Jane")
    c.last_name = overrides.get("last_name", "Doe")
    return c


def _make_lead(**overrides: Any) -> MagicMock:
    """Create a mock Lead for estimate relations."""
    lead = MagicMock()
    lead.id = overrides.get("id", uuid4())
    lead.phone = overrides.get("phone", "5125559999")
    lead.name = overrides.get("name", "Test Lead")
    lead.action_tags = overrides.get(
        "action_tags",
        [ActionTag.ESTIMATE_PENDING.value],
    )
    return lead


def _build_service(
    *,
    repo: AsyncMock | None = None,
    lead_service: AsyncMock | None = None,
    sms_service: AsyncMock | None = None,
    email_service: MagicMock | None = None,
    portal_base_url: str = "https://portal.grins.com",
) -> tuple[EstimateService, AsyncMock]:
    """Build an EstimateService with mocked dependencies."""
    estimate_repo = repo or AsyncMock()
    sms = sms_service or AsyncMock()
    sms.send_automated_message = AsyncMock(
        return_value={"success": True, "message_id": str(uuid4())},
    )
    lead_svc = lead_service or AsyncMock()
    lead_svc.update_action_tags = AsyncMock(return_value=MagicMock())
    email = email_service or MagicMock()

    svc = EstimateService(
        estimate_repository=estimate_repo,
        lead_service=lead_svc,
        sms_service=sms,
        email_service=email,
        portal_base_url=portal_base_url,
    )
    return svc, estimate_repo


# =============================================================================
# 1. Full Flow: Estimate Creation → Link Generation → Approval → Tag Update
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestEstimatePortalFullFlow:
    """Test full estimate lifecycle as user would experience.

    Estimate creation → send (link generation) → customer approval
    via portal → lead tag updated to ESTIMATE_APPROVED.

    Validates: Requirement 16.9
    """

    async def test_full_estimate_portal_approval_flow_as_user_would_experience(
        self,
    ) -> None:
        """Full flow: create → send → approve via portal → lead tag updated."""
        lead_id = uuid4()
        customer = _make_customer()
        lead = _make_lead(id=lead_id)

        svc, repo = _build_service()

        # Step 1: Create estimate
        created_est = _make_estimate(
            lead_id=lead_id,
            customer_id=customer.id,
            customer=customer,
            lead=lead,
            line_items=[
                {"item": "Drip Line", "unit_price": "50.00", "quantity": "3"},
                {"item": "Timer", "unit_price": "75.00", "quantity": "1"},
            ],
            subtotal=Decimal("225.00"),
            tax_amount=Decimal("18.56"),
            total=Decimal("243.56"),
        )
        repo.create.return_value = created_est

        data = EstimateCreate(
            lead_id=lead_id,
            customer_id=customer.id,
            line_items=[
                {"item": "Drip Line", "unit_price": "50.00", "quantity": "3"},
                {"item": "Timer", "unit_price": "75.00", "quantity": "1"},
            ],
            tax_amount=Decimal("18.56"),
        )
        staff_id = uuid4()
        result = await svc.create_estimate(data, staff_id)

        assert result.id == created_est.id
        assert result.status == EstimateStatus.DRAFT

        # Step 2: Send estimate (generates portal link)
        sent_est = _make_estimate(
            id=created_est.id,
            status=EstimateStatus.SENT.value,
            customer_token=created_est.customer_token,
            customer=customer,
            lead=lead,
            lead_id=lead_id,
        )
        repo.get_by_id.return_value = sent_est
        repo.update.return_value = sent_est
        repo.create_follow_up.return_value = MagicMock()

        send_result = await svc.send_estimate(created_est.id)

        assert send_result.portal_url.startswith("https://portal.grins.com/estimates/")
        assert str(sent_est.customer_token) in send_result.portal_url
        assert "sms" in send_result.sent_via

        # Step 3: Customer approves via portal
        approved_est = _make_estimate(
            id=created_est.id,
            status=EstimateStatus.APPROVED.value,
            approved_at=datetime.now(tz=timezone.utc),
            approved_ip="192.168.1.1",
            approved_user_agent="Mozilla/5.0",
            token_readonly=True,
            customer_token=created_est.customer_token,
            lead_id=lead_id,
            lead=lead,
        )
        repo.get_by_token.return_value = sent_est
        repo.update.return_value = approved_est
        repo.cancel_follow_ups_for_estimate.return_value = 4

        approval = await svc.approve_via_portal(
            token=created_est.customer_token,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert approval.status == EstimateStatus.APPROVED
        assert approval.approved_at is not None
        assert approval.token_readonly is True

        # Verify lead tag was updated to ESTIMATE_APPROVED
        svc.lead_service.update_action_tags.assert_called_once_with(  # type: ignore[union-attr]
            lead_id,
            add_tags=[ActionTag.ESTIMATE_APPROVED],
            remove_tags=[ActionTag.ESTIMATE_PENDING],
        )

        # Verify follow-ups were cancelled
        repo.cancel_follow_ups_for_estimate.assert_called_once_with(
            created_est.id,
        )

    async def test_full_estimate_portal_rejection_flow_as_user_would_experience(
        self,
    ) -> None:
        """Full flow: create → send → reject via portal → lead tag updated."""
        lead_id = uuid4()
        customer = _make_customer()
        lead = _make_lead(id=lead_id)

        svc, repo = _build_service()

        # Create and send
        est = _make_estimate(
            lead_id=lead_id,
            customer_id=customer.id,
            customer=customer,
            lead=lead,
            status=EstimateStatus.SENT.value,
        )
        repo.get_by_token.return_value = est

        rejected_est = _make_estimate(
            id=est.id,
            status=EstimateStatus.REJECTED.value,
            rejected_at=datetime.now(tz=timezone.utc),
            rejection_reason="Too expensive",
            token_readonly=True,
            lead_id=lead_id,
            lead=lead,
        )
        repo.update.return_value = rejected_est
        repo.cancel_follow_ups_for_estimate.return_value = 3

        rejection = await svc.reject_via_portal(
            token=est.customer_token,
            reason="Too expensive",
        )

        assert rejection.status == EstimateStatus.REJECTED
        assert rejection.rejected_at is not None
        assert rejection.rejection_reason == "Too expensive"

        # Verify lead tag updated to ESTIMATE_REJECTED
        svc.lead_service.update_action_tags.assert_called_once_with(  # type: ignore[union-attr]
            lead_id,
            add_tags=[ActionTag.ESTIMATE_REJECTED],
            remove_tags=[ActionTag.ESTIMATE_PENDING],
        )

        # Verify follow-ups cancelled
        repo.cancel_follow_ups_for_estimate.assert_called_once_with(est.id)

    async def test_portal_approval_with_expired_token_raises_error(
        self,
    ) -> None:
        """Expired portal token raises EstimateTokenExpiredError."""
        svc, repo = _build_service()

        expired_est = _make_estimate(
            token_expires_at=datetime.now(tz=timezone.utc) - timedelta(days=1),
        )
        repo.get_by_token.return_value = expired_est

        with pytest.raises(EstimateTokenExpiredError):
            await svc.approve_via_portal(
                token=expired_est.customer_token,
                ip_address="10.0.0.1",
                user_agent="TestAgent",
            )

    async def test_portal_approval_on_already_decided_estimate_raises_error(
        self,
    ) -> None:
        """Approving an already-approved estimate raises error."""
        svc, repo = _build_service()

        already_approved = _make_estimate(
            approved_at=datetime.now(tz=timezone.utc),
        )
        repo.get_by_token.return_value = already_approved

        with pytest.raises(EstimateAlreadyApprovedError):
            await svc.approve_via_portal(
                token=already_approved.customer_token,
                ip_address="10.0.0.1",
                user_agent="TestAgent",
            )

    async def test_portal_token_not_found_raises_error(self) -> None:
        """Non-existent portal token raises EstimateNotFoundError."""
        svc, repo = _build_service()
        repo.get_by_token.return_value = None

        with pytest.raises(EstimateNotFoundError):
            await svc.approve_via_portal(
                token=uuid4(),
                ip_address="10.0.0.1",
                user_agent="TestAgent",
            )


# =============================================================================
# 2. Estimate Creation from Template with Customized Line Items
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestEstimateFromTemplate:
    """Test estimate creation from template with customized line items.

    Validates: Requirement 17.8
    """

    async def test_create_from_template_with_custom_items_as_user_would_experience(
        self,
    ) -> None:
        """Admin selects template, customizes line items, creates estimate."""
        template_id = uuid4()
        lead_id = uuid4()
        staff_id = uuid4()

        template = _make_template(
            id=template_id,
            line_items=[
                {"item": "Controller", "unit_price": "150.00", "quantity": "1"},
                {"item": "Valve", "unit_price": "45.00", "quantity": "6"},
                {"item": "Sprinkler Head", "unit_price": "12.00", "quantity": "20"},
            ],
            terms="Net 30",
        )

        svc, repo = _build_service()
        repo.get_template_by_id.return_value = template

        # User overrides: changes quantity of sprinkler heads, adds new item
        custom_line_items = [
            {"item": "Controller", "unit_price": "150.00", "quantity": "1"},
            {"item": "Valve", "unit_price": "45.00", "quantity": "8"},
            {"item": "Sprinkler Head", "unit_price": "12.00", "quantity": "30"},
            {"item": "Drip Emitter", "unit_price": "3.50", "quantity": "50"},
        ]

        # Expected subtotal: 150 + 360 + 360 + 175 = 1045
        created_est = _make_estimate(
            lead_id=lead_id,
            template_id=template_id,
            line_items=custom_line_items,
            subtotal=Decimal("1045.00"),
            tax_amount=Decimal(0),
            discount_amount=Decimal(0),
            total=Decimal("1045.00"),
            notes="Net 30",
        )
        repo.create.return_value = created_est

        result = await svc.create_from_template(
            template_id=template_id,
            overrides={
                "lead_id": lead_id,
                "line_items": custom_line_items,
            },
            created_by=staff_id,
        )

        assert result.id == created_est.id
        assert result.template_id == template_id

        # Verify create was called with customized line items
        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["template_id"] == template_id
        assert create_kwargs["line_items"] == custom_line_items
        assert len(create_kwargs["line_items"]) == 4

    async def test_create_from_template_uses_template_defaults_when_no_overrides(
        self,
    ) -> None:
        """Template line items are used when no overrides provided."""
        template_id = uuid4()
        staff_id = uuid4()

        template_items = [
            {"item": "Basic Valve", "unit_price": "30.00", "quantity": "4"},
        ]
        template = _make_template(
            id=template_id,
            line_items=template_items,
            terms="Due on completion",
        )

        svc, repo = _build_service()
        repo.get_template_by_id.return_value = template

        created_est = _make_estimate(
            template_id=template_id,
            line_items=template_items,
            subtotal=Decimal("120.00"),
            total=Decimal("120.00"),
            notes="Due on completion",
        )
        repo.create.return_value = created_est

        result = await svc.create_from_template(
            template_id=template_id,
            overrides={},
            created_by=staff_id,
        )

        assert result.id == created_est.id
        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["line_items"] == template_items
        # Notes should come from template terms
        assert create_kwargs.get("notes") is not None

    async def test_create_from_nonexistent_template_raises_error(
        self,
    ) -> None:
        """Using a non-existent template raises EstimateTemplateNotFoundError."""
        svc, repo = _build_service()
        repo.get_template_by_id.return_value = None

        with pytest.raises(EstimateTemplateNotFoundError):
            await svc.create_from_template(
                template_id=uuid4(),
                overrides={},
                created_by=uuid4(),
            )


# =============================================================================
# 3. Follow-Up Lifecycle: Sent → Scheduled → Approve → Cancelled
# =============================================================================


@pytest.mark.functional
@pytest.mark.asyncio
class TestEstimateFollowUpLifecycle:
    """Test estimate follow-up lifecycle as user would experience.

    Estimate sent → follow-ups scheduled at Day 3, 7, 14, 21 →
    customer approves → remaining follow-ups cancelled.

    Validates: Requirement 51.8
    """

    async def test_follow_up_lifecycle_sent_to_approval_cancels_remaining(
        self,
    ) -> None:
        """Full lifecycle: send schedules follow-ups, approval cancels them."""
        customer = _make_customer()
        lead = _make_lead()
        est_id = uuid4()

        svc, repo = _build_service()

        # Step 1: Send estimate — should schedule follow-ups
        est = _make_estimate(
            id=est_id,
            status=EstimateStatus.DRAFT.value,
            customer=customer,
            lead=lead,
            lead_id=lead.id,
        )
        sent_est = _make_estimate(
            id=est_id,
            status=EstimateStatus.SENT.value,
            customer=customer,
            lead=lead,
            lead_id=lead.id,
            customer_token=est.customer_token,
        )
        repo.get_by_id.return_value = est
        repo.update.return_value = sent_est
        repo.create_follow_up.return_value = MagicMock()

        send_result = await svc.send_estimate(est_id)
        assert send_result.estimate_id == est_id

        # Verify 4 follow-ups were scheduled (Day 3, 7, 14, 21)
        assert repo.create_follow_up.call_count == len(FOLLOW_UP_DAYS)

        # Verify follow-up scheduling details
        follow_up_calls = repo.create_follow_up.call_args_list
        for i, call in enumerate(follow_up_calls):
            kwargs = call[1]
            assert kwargs["estimate_id"] == est_id
            assert kwargs["follow_up_number"] == i + 1
            assert kwargs["status"] == FollowUpStatus.SCHEDULED.value
            assert kwargs["channel"] == "sms"

        # Verify later follow-ups (Day 14, 21) get promotion codes
        fu3_kwargs = follow_up_calls[2][1]
        fu4_kwargs = follow_up_calls[3][1]
        assert fu3_kwargs["promotion_code"] == "SAVE10"
        assert fu4_kwargs["promotion_code"] == "SAVE10"

        # Earlier follow-ups (Day 3, 7) have no promo
        fu1_kwargs = follow_up_calls[0][1]
        fu2_kwargs = follow_up_calls[1][1]
        assert fu1_kwargs["promotion_code"] is None
        assert fu2_kwargs["promotion_code"] is None

        # Step 2: Customer approves — remaining follow-ups cancelled
        approved_est = _make_estimate(
            id=est_id,
            status=EstimateStatus.APPROVED.value,
            approved_at=datetime.now(tz=timezone.utc),
            token_readonly=True,
            lead_id=lead.id,
            lead=lead,
        )
        repo.get_by_token.return_value = sent_est
        repo.update.return_value = approved_est
        repo.cancel_follow_ups_for_estimate.return_value = 4

        approval = await svc.approve_via_portal(
            token=est.customer_token,
            ip_address="10.0.0.1",
            user_agent="Safari/17",
        )

        assert approval.status == EstimateStatus.APPROVED
        repo.cancel_follow_ups_for_estimate.assert_called_once_with(est_id)

    async def test_follow_up_processing_sends_due_follow_ups(
        self,
    ) -> None:
        """Background job sends follow-ups that are past scheduled_at."""
        customer = _make_customer()
        est = _make_estimate(
            customer=customer,
            approved_at=None,
            rejected_at=None,
        )

        fu1 = _make_follow_up(
            estimate_id=est.id,
            follow_up_number=1,
            scheduled_at=datetime.now(tz=timezone.utc) - timedelta(hours=2),
        )
        fu2 = _make_follow_up(
            estimate_id=est.id,
            follow_up_number=2,
            scheduled_at=datetime.now(tz=timezone.utc) - timedelta(minutes=30),
            promotion_code="SAVE10",
        )

        svc, repo = _build_service()
        repo.get_pending_follow_ups.return_value = [fu1, fu2]
        repo.get_by_id.return_value = est

        count = await svc.process_follow_ups()

        assert count == 2
        assert fu1.status == FollowUpStatus.SENT.value
        assert fu2.status == FollowUpStatus.SENT.value
        assert fu1.sent_at is not None
        assert fu2.sent_at is not None

    async def test_follow_up_for_already_approved_estimate_is_cancelled(
        self,
    ) -> None:
        """Follow-ups for approved estimates are cancelled, not sent."""
        est = _make_estimate(
            approved_at=datetime.now(tz=timezone.utc),
        )
        fu = _make_follow_up(estimate_id=est.id)

        svc, repo = _build_service()
        repo.get_pending_follow_ups.return_value = [fu]
        repo.get_by_id.return_value = est
        repo.cancel_follow_ups_for_estimate.return_value = 1

        count = await svc.process_follow_ups()

        assert count == 0
        repo.cancel_follow_ups_for_estimate.assert_called_once_with(est.id)

    async def test_rejection_also_cancels_remaining_follow_ups(
        self,
    ) -> None:
        """Rejecting an estimate cancels all remaining follow-ups."""
        lead = _make_lead()
        est = _make_estimate(
            status=EstimateStatus.SENT.value,
            lead_id=lead.id,
            lead=lead,
        )

        svc, repo = _build_service()
        repo.get_by_token.return_value = est

        rejected_est = _make_estimate(
            id=est.id,
            status=EstimateStatus.REJECTED.value,
            rejected_at=datetime.now(tz=timezone.utc),
            token_readonly=True,
            lead_id=lead.id,
            lead=lead,
        )
        repo.update.return_value = rejected_est
        repo.cancel_follow_ups_for_estimate.return_value = 3

        await svc.reject_via_portal(
            token=est.customer_token,
            reason="Found another vendor",
        )

        repo.cancel_follow_ups_for_estimate.assert_called_once_with(est.id)

    async def test_send_estimate_without_sms_service_still_schedules_follow_ups(
        self,
    ) -> None:
        """Even without SMS, follow-ups are scheduled for later delivery."""
        est = _make_estimate(
            customer=None,
            lead=None,
        )

        svc, repo = _build_service(sms_service=AsyncMock())
        repo.get_by_id.return_value = est
        repo.update.return_value = est
        repo.create_follow_up.return_value = MagicMock()

        result = await svc.send_estimate(est.id)

        assert result.estimate_id == est.id
        assert repo.create_follow_up.call_count == len(FOLLOW_UP_DAYS)
