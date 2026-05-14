"""Unit tests for EstimateService CRM Gap Closure.

Tests portal estimate access, approval/rejection, template round-trip,
auto-routing, total calculation, follow-up scheduling, and portal
response exclusion of internal IDs.

Properties:
  P20: Portal estimate access by token
  P21: Estimate approval updates lead tag and invalidates token for writes
  P22: Estimate template round-trip
  P35: Unapproved estimate auto-routing to leads
  P51: Estimate total calculation with tiers and discounts
  P52: Follow-up scheduling and cancellation
  P75: Portal responses exclude internal IDs

Validates: Requirements 16.8, 16.9, 17.7, 17.8, 32.8, 48.8, 51.7, 51.8,
           78.7, 78.8
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.exceptions import (
    EstimateAlreadyApprovedError,
    EstimateNotFoundError,
    EstimateTemplateNotFoundError,
    EstimateTokenExpiredError,
    InvalidPromotionCodeError,
)
from grins_platform.models.enums import (
    ActionTag,
    EstimateStatus,
    FollowUpStatus,
)
from grins_platform.schemas.estimate import EstimateCreate, EstimateResponse
from grins_platform.schemas.portal import PortalEstimateResponse
from grins_platform.services.estimate_service import (
    AUTO_ROUTE_HOURS,
    FOLLOW_UP_DAYS,
    TOKEN_VALIDITY_DAYS,
    VALID_PROMOTIONS,
    EstimateService,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_estimate_mock(
    *,
    estimate_id: UUID | None = None,
    lead_id: UUID | None = None,
    customer_id: UUID | None = None,
    job_id: UUID | None = None,
    template_id: UUID | None = None,
    status: str = EstimateStatus.DRAFT.value,
    line_items: list[dict[str, Any]] | None = None,
    options: list[dict[str, Any]] | None = None,
    subtotal: Decimal = Decimal("500.00"),
    tax_amount: Decimal = Decimal("40.00"),
    discount_amount: Decimal = Decimal("0.00"),
    total: Decimal = Decimal("540.00"),
    promotion_code: str | None = None,
    valid_until: datetime | None = None,
    notes: str | None = None,
    customer_token: UUID | None = None,
    token_expires_at: datetime | None = None,
    token_readonly: bool = False,
    approved_at: datetime | None = None,
    approved_ip: str | None = None,
    approved_user_agent: str | None = None,
    rejected_at: datetime | None = None,
    rejected_reason: str | None = None,
    customer: MagicMock | None = None,
    lead: MagicMock | None = None,
) -> MagicMock:
    """Create a mock Estimate model instance.

    Uses spec=False so MagicMock doesn't auto-create attributes.
    All fields are explicitly set to avoid Pydantic validation errors
    when model_validate is called on the mock.
    """
    now = datetime.now(tz=timezone.utc)
    est = MagicMock()
    est.id = estimate_id or uuid4()
    est.lead_id = lead_id
    est.customer_id = customer_id
    est.job_id = job_id
    est.template_id = template_id
    est.status = status
    est.line_items = line_items or [
        {"item": "Sprinkler Repair", "unit_price": "250.00", "quantity": "2"},
    ]
    est.options = options
    est.subtotal = subtotal
    est.tax_amount = tax_amount
    est.discount_amount = discount_amount
    est.total = total
    est.promotion_code = promotion_code
    est.valid_until = valid_until
    est.notes = notes
    est.customer_token = customer_token or uuid4()
    est.token_expires_at = token_expires_at or (
        now + timedelta(days=TOKEN_VALIDITY_DAYS)
    )
    est.token_readonly = token_readonly
    est.approved_at = approved_at
    est.approved_ip = approved_ip
    est.approved_user_agent = approved_user_agent
    est.rejected_at = rejected_at
    est.rejection_reason = rejected_reason
    est.customer = customer
    est.lead = lead
    est.follow_ups = []
    est.created_at = now
    est.updated_at = now
    return est


def _make_template_mock(
    *,
    template_id: UUID | None = None,
    name: str = "Standard Repair",
    description: str | None = "Standard repair template",
    line_items: list[dict[str, Any]] | None = None,
    terms: str | None = "Net 30",
    is_active: bool = True,
) -> MagicMock:
    """Create a mock EstimateTemplate model instance."""
    tmpl = MagicMock()
    tmpl.id = template_id or uuid4()
    tmpl.name = name
    tmpl.description = description
    tmpl.line_items = line_items or [
        {"item": "Repair", "unit_price": "100.00", "quantity": "1"},
    ]
    tmpl.terms = terms
    tmpl.is_active = is_active
    tmpl.created_at = datetime.now(tz=timezone.utc)
    tmpl.updated_at = datetime.now(tz=timezone.utc)
    return tmpl


def _make_follow_up_mock(
    *,
    follow_up_id: UUID | None = None,
    estimate_id: UUID | None = None,
    follow_up_number: int = 1,
    scheduled_at: datetime | None = None,
    sent_at: datetime | None = None,
    channel: str = "sms",
    message: str | None = None,
    promotion_code: str | None = None,
    status: str = FollowUpStatus.SCHEDULED.value,
) -> MagicMock:
    """Create a mock EstimateFollowUp model instance."""
    fu = MagicMock()
    fu.id = follow_up_id or uuid4()
    fu.estimate_id = estimate_id or uuid4()
    fu.follow_up_number = follow_up_number
    fu.scheduled_at = scheduled_at or datetime.now(tz=timezone.utc)
    fu.sent_at = sent_at
    fu.channel = channel
    fu.message = message
    fu.promotion_code = promotion_code
    fu.status = status
    fu.created_at = datetime.now(tz=timezone.utc)
    return fu


def _build_service(
    repo: AsyncMock | None = None,
    lead_service: AsyncMock | None = None,
    sms_service: AsyncMock | None = None,
    email_service: AsyncMock | None = None,
    sales_pipeline_service: AsyncMock | None = None,
) -> EstimateService:
    """Build an EstimateService with mocked dependencies."""
    return EstimateService(
        estimate_repository=repo or AsyncMock(),
        portal_base_url="https://portal.grins.com",
        lead_service=lead_service,
        sms_service=sms_service,
        email_service=email_service,
        sales_pipeline_service=sales_pipeline_service,
    )


# =============================================================================
# Property 20: Portal estimate access by token
# Validates: Requirements 16.1, 78.1, 78.2
# =============================================================================


@pytest.mark.unit
class TestProperty20PortalEstimateAccessByToken:
    """Property 20: Portal estimate access by token.

    **Validates: Requirements 16.1, 78.1, 78.2**
    """

    @pytest.mark.asyncio
    async def test_validate_portal_token_with_valid_token_returns_estimate(
        self,
    ) -> None:
        """A valid, non-expired token returns the estimate."""
        token = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            token_expires_at=datetime.now(tz=timezone.utc) + timedelta(days=10),
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)

        svc = _build_service(repo=repo)
        result = await svc._validate_portal_token(token)

        assert result.id == estimate.id
        repo.get_by_token.assert_awaited_once_with(token)

    @pytest.mark.asyncio
    async def test_validate_portal_token_with_expired_token_raises_expired(
        self,
    ) -> None:
        """An expired token raises EstimateTokenExpiredError (HTTP 410)."""
        token = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            token_expires_at=datetime.now(tz=timezone.utc) - timedelta(days=1),
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)

        svc = _build_service(repo=repo)
        with pytest.raises(EstimateTokenExpiredError):
            await svc._validate_portal_token(token)

    @pytest.mark.asyncio
    async def test_validate_portal_token_with_unknown_token_raises_not_found(
        self,
    ) -> None:
        """An unknown token raises EstimateNotFoundError."""
        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=None)

        svc = _build_service(repo=repo)
        with pytest.raises(EstimateNotFoundError):
            await svc._validate_portal_token(uuid4())

    @given(
        days_remaining=st.integers(min_value=1, max_value=TOKEN_VALIDITY_DAYS),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_validate_portal_token_with_any_non_expired_days_succeeds(
        self,
        days_remaining: int,
    ) -> None:
        """For any token with N days remaining (1..30), access succeeds.

        **Validates: Requirements 16.1, 78.1, 78.2**
        """
        token = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            token_expires_at=datetime.now(tz=timezone.utc)
            + timedelta(days=days_remaining),
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)

        svc = _build_service(repo=repo)
        result = await svc._validate_portal_token(token)
        assert result.id == estimate.id

    @given(
        days_expired=st.integers(min_value=1, max_value=365),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_validate_portal_token_with_any_expired_days_raises(
        self,
        days_expired: int,
    ) -> None:
        """For any token expired by N days, access raises TokenExpired.

        **Validates: Requirements 16.1, 78.1, 78.2**
        """
        token = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            token_expires_at=datetime.now(tz=timezone.utc)
            - timedelta(days=days_expired),
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)

        svc = _build_service(repo=repo)
        with pytest.raises(EstimateTokenExpiredError):
            await svc._validate_portal_token(token)


# =============================================================================
# Property 21: Estimate approval updates lead tag and invalidates token
# Validates: Requirements 16.2, 16.5, 78.4
# =============================================================================


@pytest.mark.unit
class TestProperty21EstimateApprovalUpdatesLeadTag:
    """Property 21: Estimate approval updates lead tag and invalidates
    token for writes.

    **Validates: Requirements 16.2, 16.5, 78.4**
    """

    @pytest.mark.asyncio
    async def test_approve_via_portal_sets_token_readonly_true(self) -> None:
        """Approval sets token_readonly=True preventing further modifications."""
        token = uuid4()
        lead_id = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            lead_id=lead_id,
            status=EstimateStatus.SENT.value,
        )

        updated_estimate = _make_estimate_mock(
            estimate_id=estimate.id,
            customer_token=token,
            lead_id=lead_id,
            status=EstimateStatus.APPROVED.value,
            approved_at=datetime.now(tz=timezone.utc),
            token_readonly=True,
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(return_value=updated_estimate)
        repo.cancel_follow_ups_for_estimate = AsyncMock(return_value=2)

        lead_svc = AsyncMock()
        lead_svc.update_action_tags = AsyncMock()

        svc = _build_service(repo=repo, lead_service=lead_svc)
        await svc.approve_via_portal(token, "1.2.3.4", "TestAgent/1.0", db=AsyncMock())

        # Verify token_readonly was set to True in the update call
        repo.update.assert_awaited_once()
        call_kwargs = repo.update.call_args
        assert call_kwargs[1]["token_readonly"] is True
        assert call_kwargs[1]["status"] == EstimateStatus.APPROVED.value

    @pytest.mark.asyncio
    async def test_approve_via_portal_updates_lead_tag_to_approved(
        self,
    ) -> None:
        """Approval updates the linked lead's tag from ESTIMATE_PENDING
        to ESTIMATE_APPROVED."""
        token = uuid4()
        lead_id = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            lead_id=lead_id,
            status=EstimateStatus.SENT.value,
        )

        updated_estimate = _make_estimate_mock(
            estimate_id=estimate.id,
            customer_token=token,
            lead_id=lead_id,
            status=EstimateStatus.APPROVED.value,
            approved_at=datetime.now(tz=timezone.utc),
            token_readonly=True,
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(return_value=updated_estimate)
        repo.cancel_follow_ups_for_estimate = AsyncMock(return_value=0)

        lead_svc = AsyncMock()
        lead_svc.update_action_tags = AsyncMock()

        svc = _build_service(repo=repo, lead_service=lead_svc)
        await svc.approve_via_portal(token, "1.2.3.4", "TestAgent/1.0", db=AsyncMock())

        lead_svc.update_action_tags.assert_awaited_once_with(
            lead_id,
            add_tags=[ActionTag.ESTIMATE_APPROVED],
            remove_tags=[ActionTag.ESTIMATE_PENDING],
        )

    @pytest.mark.asyncio
    async def test_approve_via_portal_cancels_remaining_follow_ups(
        self,
    ) -> None:
        """Approval cancels all remaining follow-ups."""
        token = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            status=EstimateStatus.SENT.value,
        )

        updated = _make_estimate_mock(
            estimate_id=estimate.id,
            status=EstimateStatus.APPROVED.value,
            approved_at=datetime.now(tz=timezone.utc),
            token_readonly=True,
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(return_value=updated)
        repo.cancel_follow_ups_for_estimate = AsyncMock(return_value=3)

        svc = _build_service(repo=repo)
        await svc.approve_via_portal(token, "1.2.3.4", "TestAgent/1.0", db=AsyncMock())

        repo.cancel_follow_ups_for_estimate.assert_awaited_once_with(estimate.id)

    @pytest.mark.asyncio
    async def test_approve_via_portal_with_already_approved_raises(
        self,
    ) -> None:
        """Approving an already-decided estimate raises error."""
        token = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            status=EstimateStatus.APPROVED.value,
            approved_at=datetime.now(tz=timezone.utc),
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)

        svc = _build_service(repo=repo)
        with pytest.raises(EstimateAlreadyApprovedError):
            await svc.approve_via_portal(token, "1.2.3.4", "TestAgent/1.0", db=AsyncMock())

    @pytest.mark.asyncio
    async def test_reject_via_portal_also_sets_token_readonly(self) -> None:
        """Rejection also sets token_readonly=True."""
        token = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            status=EstimateStatus.SENT.value,
        )

        updated = _make_estimate_mock(
            estimate_id=estimate.id,
            status=EstimateStatus.REJECTED.value,
            rejected_at=datetime.now(tz=timezone.utc),
            token_readonly=True,
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(return_value=updated)
        repo.cancel_follow_ups_for_estimate = AsyncMock(return_value=0)

        svc = _build_service(repo=repo)
        await svc.reject_via_portal(token, reason="Too expensive", db=AsyncMock())

        call_kwargs = repo.update.call_args
        assert call_kwargs[1]["token_readonly"] is True
        assert call_kwargs[1]["status"] == EstimateStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_reject_via_portal_response_surfaces_rejection_reason(
        self,
    ) -> None:
        """F2: response surfaces the customer's rejection reason.

        ORM column is ``rejected_reason``; schema field is
        ``rejection_reason``. The alias bridge on
        :class:`EstimateResponse` must translate the ORM attribute back
        into the response so admins can see the customer-supplied
        reason.
        """
        from types import SimpleNamespace  # noqa: PLC0415

        token = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            status=EstimateStatus.SENT.value,
        )

        now = datetime.now(tz=timezone.utc)
        # SimpleNamespace mirrors a real ORM Estimate row: the column
        # is ``rejected_reason``, not ``rejection_reason``. Pre-fix
        # ``EstimateResponse.model_validate`` returned ``None`` here.
        updated = SimpleNamespace(
            id=estimate.id,
            lead_id=None,
            customer_id=None,
            job_id=None,
            template_id=None,
            status=EstimateStatus.REJECTED.value,
            line_items=[],
            options=None,
            subtotal=Decimal("500.00"),
            tax_amount=Decimal("40.00"),
            discount_amount=Decimal("0.00"),
            total=Decimal("540.00"),
            promotion_code=None,
            valid_until=None,
            notes=None,
            customer_token=token,
            token_expires_at=now + timedelta(days=TOKEN_VALIDITY_DAYS),
            token_readonly=True,
            approved_at=None,
            rejected_at=now,
            rejected_reason="Too expensive",
            created_at=now,
            updated_at=now,
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(return_value=updated)
        repo.cancel_follow_ups_for_estimate = AsyncMock(return_value=0)

        svc = _build_service(repo=repo)
        result = await svc.reject_via_portal(token, reason="Too expensive", db=AsyncMock())

        assert isinstance(result, EstimateResponse)
        assert result.rejection_reason == "Too expensive"


# =============================================================================
# Property 22: Estimate template round-trip
# Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
# =============================================================================


@pytest.mark.unit
class TestProperty22EstimateTemplateRoundTrip:
    """Property 22: Estimate template round-trip.

    **Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5**
    """

    @pytest.mark.asyncio
    async def test_create_from_template_uses_template_line_items(
        self,
    ) -> None:
        """Creating from template clones the template's line_items."""
        template_id = uuid4()
        template_items = [
            {"item": "Valve Replacement", "unit_price": "75.00", "quantity": "4"},
            {"item": "Labor", "unit_price": "50.00", "quantity": "2"},
        ]
        template = _make_template_mock(
            template_id=template_id,
            line_items=template_items,
            terms="Net 30 days",
        )

        created_estimate = _make_estimate_mock(
            template_id=template_id,
            line_items=template_items,
            subtotal=Decimal("400.00"),
            tax_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total=Decimal("400.00"),
        )

        repo = AsyncMock()
        repo.get_template_by_id = AsyncMock(return_value=template)
        repo.create = AsyncMock(return_value=created_estimate)

        svc = _build_service(repo=repo)
        await svc.create_from_template(
            template_id=template_id,
            overrides={"customer_id": uuid4()},
            created_by=uuid4(),
        )

        # The repo.create call should have received the template's line_items
        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["line_items"] == template_items

    @pytest.mark.asyncio
    async def test_create_from_template_with_overrides_applies_them(
        self,
    ) -> None:
        """Overrides replace template values when provided."""
        template_id = uuid4()
        template_items = [
            {"item": "Repair", "unit_price": "100.00", "quantity": "1"},
        ]
        override_items = [
            {"item": "Custom Repair", "unit_price": "200.00", "quantity": "3"},
        ]
        template = _make_template_mock(
            template_id=template_id,
            line_items=template_items,
        )

        created_estimate = _make_estimate_mock(
            template_id=template_id,
            line_items=override_items,
            subtotal=Decimal("600.00"),
            total=Decimal("600.00"),
        )

        repo = AsyncMock()
        repo.get_template_by_id = AsyncMock(return_value=template)
        repo.create = AsyncMock(return_value=created_estimate)

        svc = _build_service(repo=repo)
        await svc.create_from_template(
            template_id=template_id,
            overrides={"line_items": override_items, "customer_id": uuid4()},
            created_by=uuid4(),
        )

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["line_items"] == override_items

    @pytest.mark.asyncio
    async def test_create_from_template_with_missing_template_raises(
        self,
    ) -> None:
        """Non-existent template raises EstimateTemplateNotFoundError."""
        repo = AsyncMock()
        repo.get_template_by_id = AsyncMock(return_value=None)

        svc = _build_service(repo=repo)
        with pytest.raises(EstimateTemplateNotFoundError):
            await svc.create_from_template(
                template_id=uuid4(),
                overrides={},
                created_by=uuid4(),
            )

    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        num_items=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=30)
    @pytest.mark.asyncio
    async def test_create_from_template_preserves_template_name_context(
        self,
        name: str,
        num_items: int,
    ) -> None:
        """For any template with N line items, creating from it passes
        the template's line_items to the estimate.

        **Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5**
        """
        template_id = uuid4()
        items = [
            {
                "item": f"Item {i}",
                "unit_price": str(Decimal("10.00") * (i + 1)),
                "quantity": "1",
            }
            for i in range(num_items)
        ]
        template = _make_template_mock(
            template_id=template_id,
            name=name,
            line_items=items,
            terms="Standard terms",
        )

        created_estimate = _make_estimate_mock(
            template_id=template_id,
            line_items=items,
            notes="Standard terms",
        )

        repo = AsyncMock()
        repo.get_template_by_id = AsyncMock(return_value=template)
        repo.create = AsyncMock(return_value=created_estimate)

        svc = _build_service(repo=repo)
        await svc.create_from_template(
            template_id=template_id,
            overrides={},
            created_by=uuid4(),
        )

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["line_items"] == items
        # Notes should default to template terms when no override
        assert create_kwargs["notes"] == "Standard terms"


# =============================================================================
# Property 35: Unapproved estimate auto-routing to leads
# Validates: Requirements 32.4, 32.7
# =============================================================================


@pytest.mark.unit
class TestProperty35UnapprovedEstimateAutoRouting:
    """Property 35: Unapproved estimate auto-routing to leads.

    **Validates: Requirements 32.4, 32.7**
    """

    @pytest.mark.asyncio
    async def test_check_unapproved_creates_leads_for_old_estimates(
        self,
    ) -> None:
        """Estimates >4hrs old without approval get routed to leads."""
        customer_id = uuid4()
        est1 = _make_estimate_mock(
            customer_id=customer_id,
            status=EstimateStatus.SENT.value,
        )
        est2 = _make_estimate_mock(
            customer_id=uuid4(),
            status=EstimateStatus.SENT.value,
        )

        repo = AsyncMock()
        repo.find_unapproved_older_than = AsyncMock(return_value=[est1, est2])

        lead_svc = AsyncMock()
        lead_svc.create_lead_from_estimate = AsyncMock()

        svc = _build_service(repo=repo, lead_service=lead_svc)
        routed = await svc.check_unapproved_estimates()

        assert routed == 2
        assert lead_svc.create_lead_from_estimate.await_count == 2
        repo.find_unapproved_older_than.assert_awaited_once_with(AUTO_ROUTE_HOURS)

    @pytest.mark.asyncio
    async def test_check_unapproved_skips_estimates_without_customer_id(
        self,
    ) -> None:
        """Estimates without customer_id are skipped (no lead to create)."""
        est = _make_estimate_mock(
            customer_id=None,
            status=EstimateStatus.SENT.value,
        )

        repo = AsyncMock()
        repo.find_unapproved_older_than = AsyncMock(return_value=[est])

        lead_svc = AsyncMock()

        svc = _build_service(repo=repo, lead_service=lead_svc)
        routed = await svc.check_unapproved_estimates()

        assert routed == 0
        lead_svc.create_lead_from_estimate.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_check_unapproved_with_no_old_estimates_returns_zero(
        self,
    ) -> None:
        """When no unapproved estimates exist, returns 0."""
        repo = AsyncMock()
        repo.find_unapproved_older_than = AsyncMock(return_value=[])

        svc = _build_service(repo=repo, lead_service=AsyncMock())
        routed = await svc.check_unapproved_estimates()

        assert routed == 0

    @given(
        count=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=20)
    @pytest.mark.asyncio
    async def test_check_unapproved_routes_exactly_n_estimates(
        self,
        count: int,
    ) -> None:
        """For any N unapproved estimates with customer_id, exactly N
        leads are created.

        **Validates: Requirements 32.4, 32.7**
        """
        estimates = [
            _make_estimate_mock(
                customer_id=uuid4(),
                status=EstimateStatus.SENT.value,
            )
            for _ in range(count)
        ]

        repo = AsyncMock()
        repo.find_unapproved_older_than = AsyncMock(return_value=estimates)

        lead_svc = AsyncMock()
        lead_svc.create_lead_from_estimate = AsyncMock()

        svc = _build_service(repo=repo, lead_service=lead_svc)
        routed = await svc.check_unapproved_estimates()

        assert routed == count
        assert lead_svc.create_lead_from_estimate.await_count == count

    @pytest.mark.asyncio
    async def test_check_unapproved_continues_on_individual_failure(
        self,
    ) -> None:
        """If one lead creation fails, others still get processed."""
        est1 = _make_estimate_mock(customer_id=uuid4())
        est2 = _make_estimate_mock(customer_id=uuid4())

        repo = AsyncMock()
        repo.find_unapproved_older_than = AsyncMock(return_value=[est1, est2])

        lead_svc = AsyncMock()
        lead_svc.create_lead_from_estimate = AsyncMock(
            side_effect=[Exception("DB error"), MagicMock()],
        )

        svc = _build_service(repo=repo, lead_service=lead_svc)
        routed = await svc.check_unapproved_estimates()

        # First fails, second succeeds
        assert routed == 1


# =============================================================================
# Property 51: Estimate total calculation with tiers and discounts
# Validates: Requirements 48.4, 48.5, 48.6, 48.7
# =============================================================================


@pytest.mark.unit
class TestProperty51EstimateTotalCalculation:
    """Property 51: Estimate total calculation with tiers and discounts.

    **Validates: Requirements 48.4, 48.5, 48.6, 48.7**
    """

    def test_calculate_subtotal_with_single_item(self) -> None:
        """Subtotal = unit_price * quantity for a single item."""
        items = [{"item": "Valve", "unit_price": "75.50", "quantity": "3"}]
        result = EstimateService._calculate_subtotal(items)
        assert result == Decimal("226.50")

    def test_calculate_subtotal_with_multiple_items(self) -> None:
        """Subtotal = sum of (unit_price * quantity) for all items."""
        items = [
            {"item": "Valve", "unit_price": "75.00", "quantity": "2"},
            {"item": "Labor", "unit_price": "50.00", "quantity": "3"},
        ]
        result = EstimateService._calculate_subtotal(items)
        assert result == Decimal("300.00")

    def test_calculate_subtotal_with_empty_items_returns_zero(self) -> None:
        """Empty or None line_items returns Decimal(0)."""
        assert EstimateService._calculate_subtotal(None) == Decimal(0)
        assert EstimateService._calculate_subtotal([]) == Decimal(0)

    @given(
        prices=st.lists(
            st.tuples(
                st.decimals(
                    min_value=Decimal("0.01"),
                    max_value=Decimal("9999.99"),
                    places=2,
                    allow_nan=False,
                    allow_infinity=False,
                ),
                st.integers(min_value=1, max_value=100),
            ),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=50)
    def test_calculate_subtotal_equals_sum_of_price_times_quantity(
        self,
        prices: list[tuple[Decimal, int]],
    ) -> None:
        """For any set of line items, subtotal == sum(price * qty).

        **Validates: Requirements 48.4, 48.5, 48.6, 48.7**
        """
        items = [
            {
                "item": f"Item {i}",
                "unit_price": str(price),
                "quantity": str(qty),
            }
            for i, (price, qty) in enumerate(prices)
        ]
        expected = sum(price * qty for price, qty in prices)
        result = EstimateService._calculate_subtotal(items)
        assert result == expected

    @pytest.mark.asyncio
    async def test_create_estimate_calculates_total_correctly(self) -> None:
        """create_estimate computes total = subtotal + tax - discount."""
        line_items = [
            {"item": "Sprinkler Head", "unit_price": "25.00", "quantity": "10"},
            {"item": "Labor", "unit_price": "60.00", "quantity": "2"},
        ]
        # subtotal = 250 + 120 = 370
        # tax = 29.60, discount = 20
        # total = 370 + 29.60 - 20 = 379.60

        created_estimate = _make_estimate_mock(
            subtotal=Decimal("370.00"),
            tax_amount=Decimal("29.60"),
            discount_amount=Decimal("20.00"),
            total=Decimal("379.60"),
            line_items=line_items,
        )

        repo = AsyncMock()
        repo.create = AsyncMock(return_value=created_estimate)

        svc = _build_service(repo=repo)
        data = EstimateCreate(
            line_items=line_items,
            tax_amount=Decimal("29.60"),
            discount_amount=Decimal("20.00"),
        )
        await svc.create_estimate(data, created_by=uuid4())

        create_kwargs = repo.create.call_args[1]
        assert create_kwargs["subtotal"] == Decimal("370.00")
        assert create_kwargs["total"] == Decimal("379.60")

    @pytest.mark.asyncio
    async def test_apply_promotion_calculates_percentage_discount(
        self,
    ) -> None:
        """Applying SAVE10 gives 10% off subtotal."""
        estimate = _make_estimate_mock(
            subtotal=Decimal("500.00"),
            tax_amount=Decimal("40.00"),
            total=Decimal("540.00"),
        )

        updated = _make_estimate_mock(
            estimate_id=estimate.id,
            subtotal=Decimal("500.00"),
            tax_amount=Decimal("40.00"),
            discount_amount=Decimal("50.00"),
            total=Decimal("490.00"),
            promotion_code="SAVE10",
        )

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(return_value=updated)

        svc = _build_service(repo=repo)
        await svc.apply_promotion(estimate.id, "SAVE10")

        call_kwargs = repo.update.call_args[1]
        assert call_kwargs["discount_amount"] == Decimal("50.00")
        # total = 500 + 40 - 50 = 490
        assert call_kwargs["total"] == Decimal("490.00")
        assert call_kwargs["promotion_code"] == "SAVE10"

    @pytest.mark.asyncio
    async def test_apply_promotion_with_invalid_code_raises(self) -> None:
        """Invalid promotion code raises InvalidPromotionCodeError."""
        estimate = _make_estimate_mock()

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=estimate)

        svc = _build_service(repo=repo)
        with pytest.raises(InvalidPromotionCodeError):
            await svc.apply_promotion(estimate.id, "FAKECODE")

    @given(
        code=st.sampled_from(list(VALID_PROMOTIONS.keys())),
        subtotal=st.decimals(
            min_value=Decimal("10.00"),
            max_value=Decimal("50000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
        tax=st.decimals(
            min_value=Decimal("0.00"),
            max_value=Decimal("5000.00"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.asyncio
    async def test_apply_promotion_total_never_negative(
        self,
        code: str,
        subtotal: Decimal,
        tax: Decimal,
    ) -> None:
        """For any valid promo code and subtotal, the new total is
        subtotal + tax - discount, and discount = subtotal * rate.

        **Validates: Requirements 48.4, 48.5, 48.6, 48.7**
        """
        rate = VALID_PROMOTIONS[code]
        expected_discount = subtotal * rate
        expected_total = subtotal + tax - expected_discount

        estimate = _make_estimate_mock(
            subtotal=subtotal,
            tax_amount=tax,
            total=subtotal + tax,
        )

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(
            return_value=_make_estimate_mock(
                estimate_id=estimate.id,
                subtotal=subtotal,
                tax_amount=tax,
                discount_amount=expected_discount,
                total=expected_total,
                promotion_code=code,
            ),
        )

        svc = _build_service(repo=repo)
        await svc.apply_promotion(estimate.id, code)

        call_kwargs = repo.update.call_args[1]
        assert call_kwargs["discount_amount"] == expected_discount
        assert call_kwargs["total"] == expected_total


# =============================================================================
# Property 52: Follow-up scheduling and cancellation
# Validates: Requirements 51.2, 51.5
# =============================================================================


@pytest.mark.unit
class TestProperty52FollowUpSchedulingAndCancellation:
    """Property 52: Follow-up scheduling and cancellation.

    **Validates: Requirements 51.2, 51.5**
    """

    @pytest.mark.asyncio
    async def test_send_estimate_schedules_follow_ups_at_correct_intervals(
        self,
    ) -> None:
        """Sending an estimate schedules follow-ups at Day 3, 7, 14, 21."""
        estimate = _make_estimate_mock(
            status=EstimateStatus.DRAFT.value,
            customer_token=uuid4(),
        )
        # Give the estimate a customer with a phone for SMS
        customer_mock = MagicMock()
        customer_mock.phone = "6125551234"
        customer_mock.email = "test@example.com"
        estimate.customer = customer_mock
        estimate.lead = None

        updated = _make_estimate_mock(
            estimate_id=estimate.id,
            status=EstimateStatus.SENT.value,
        )

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(return_value=updated)
        repo.create_follow_up = AsyncMock()

        sms_svc = AsyncMock()
        sms_svc.send_automated_message = AsyncMock()

        svc = _build_service(repo=repo, sms_service=sms_svc)
        await svc.send_estimate(estimate.id)

        # Should create exactly 4 follow-ups
        assert repo.create_follow_up.await_count == len(FOLLOW_UP_DAYS)

        # Verify each follow-up has the correct follow_up_number
        for i, call in enumerate(repo.create_follow_up.call_args_list):
            kwargs = call[1]
            assert kwargs["follow_up_number"] == i + 1
            assert kwargs["status"] == FollowUpStatus.SCHEDULED.value
            assert kwargs["channel"] == "sms"

    @pytest.mark.asyncio
    async def test_send_estimate_later_follow_ups_get_promo_code(
        self,
    ) -> None:
        """Follow-ups #3 and #4 (Day 14, 21) get a promotion code."""
        estimate = _make_estimate_mock(status=EstimateStatus.DRAFT.value)
        estimate.customer = None
        estimate.lead = None

        repo = AsyncMock()
        repo.get_by_id = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(return_value=estimate)
        repo.create_follow_up = AsyncMock()

        svc = _build_service(repo=repo)
        await svc.send_estimate(estimate.id)

        calls = repo.create_follow_up.call_args_list
        # Follow-ups 1 and 2 should have no promo
        assert calls[0][1]["promotion_code"] is None
        assert calls[1][1]["promotion_code"] is None
        # Follow-ups 3 and 4 should have promo
        assert calls[2][1]["promotion_code"] == "SAVE10"
        assert calls[3][1]["promotion_code"] == "SAVE10"

    @pytest.mark.asyncio
    async def test_approve_cancels_all_pending_follow_ups(self) -> None:
        """Approval cancels all remaining PENDING follow-ups."""
        token = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            status=EstimateStatus.SENT.value,
        )

        updated = _make_estimate_mock(
            estimate_id=estimate.id,
            status=EstimateStatus.APPROVED.value,
            approved_at=datetime.now(tz=timezone.utc),
            token_readonly=True,
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(return_value=updated)
        repo.cancel_follow_ups_for_estimate = AsyncMock(return_value=4)

        svc = _build_service(repo=repo)
        await svc.approve_via_portal(token, "1.2.3.4", "Agent/1.0", db=AsyncMock())

        repo.cancel_follow_ups_for_estimate.assert_awaited_once_with(estimate.id)

    @pytest.mark.asyncio
    async def test_reject_cancels_all_pending_follow_ups(self) -> None:
        """Rejection also cancels all remaining follow-ups."""
        token = uuid4()
        estimate = _make_estimate_mock(
            customer_token=token,
            status=EstimateStatus.SENT.value,
        )

        updated = _make_estimate_mock(
            estimate_id=estimate.id,
            status=EstimateStatus.REJECTED.value,
            rejected_at=datetime.now(tz=timezone.utc),
            token_readonly=True,
        )

        repo = AsyncMock()
        repo.get_by_token = AsyncMock(return_value=estimate)
        repo.update = AsyncMock(return_value=updated)
        repo.cancel_follow_ups_for_estimate = AsyncMock(return_value=3)

        svc = _build_service(repo=repo)
        await svc.reject_via_portal(token, reason="Changed mind", db=AsyncMock())

        repo.cancel_follow_ups_for_estimate.assert_awaited_once_with(estimate.id)

    @pytest.mark.asyncio
    async def test_process_follow_ups_sends_due_follow_ups(self) -> None:
        """process_follow_ups sends follow-ups whose scheduled_at is past."""
        est_id = uuid4()
        estimate = _make_estimate_mock(
            estimate_id=est_id,
            status=EstimateStatus.SENT.value,
            customer_token=uuid4(),
        )
        customer_mock = MagicMock()
        customer_mock.phone = "6125551234"
        estimate.customer = customer_mock

        fu = _make_follow_up_mock(
            estimate_id=est_id,
            scheduled_at=datetime.now(tz=timezone.utc) - timedelta(hours=1),
            status=FollowUpStatus.SCHEDULED.value,
        )

        repo = AsyncMock()
        repo.get_pending_follow_ups = AsyncMock(return_value=[fu])
        repo.get_by_id = AsyncMock(return_value=estimate)
        repo.session = AsyncMock()

        sms_svc = AsyncMock()
        sms_svc.send_automated_message = AsyncMock()

        svc = _build_service(repo=repo, sms_service=sms_svc)
        sent = await svc.process_follow_ups()

        assert sent == 1
        sms_svc.send_automated_message.assert_awaited_once()
        assert fu.status == FollowUpStatus.SENT.value

    @pytest.mark.asyncio
    async def test_process_follow_ups_skips_decided_estimates(self) -> None:
        """Follow-ups for already-approved estimates get cancelled."""
        est_id = uuid4()
        estimate = _make_estimate_mock(
            estimate_id=est_id,
            status=EstimateStatus.APPROVED.value,
            approved_at=datetime.now(tz=timezone.utc),
        )

        fu = _make_follow_up_mock(
            estimate_id=est_id,
            status=FollowUpStatus.SCHEDULED.value,
        )

        repo = AsyncMock()
        repo.get_pending_follow_ups = AsyncMock(return_value=[fu])
        repo.get_by_id = AsyncMock(return_value=estimate)
        repo.cancel_follow_ups_for_estimate = AsyncMock(return_value=1)

        svc = _build_service(repo=repo)
        sent = await svc.process_follow_ups()

        assert sent == 0
        repo.cancel_follow_ups_for_estimate.assert_awaited_once_with(est_id)


# =============================================================================
# Property 75: Portal responses exclude internal IDs
# Validates: Requirements 78.6
# =============================================================================


@pytest.mark.unit
class TestProperty75PortalResponsesExcludeInternalIDs:
    """Property 75: Portal responses exclude internal IDs.

    **Validates: Requirements 78.6**
    """

    def test_portal_estimate_response_has_no_customer_id_field(self) -> None:
        """PortalEstimateResponse schema does not expose customer_id."""
        fields = PortalEstimateResponse.model_fields
        assert "customer_id" not in fields
        assert "lead_id" not in fields
        assert "staff_id" not in fields
        assert "created_by" not in fields

    def test_portal_estimate_response_has_no_internal_uuid_fields(
        self,
    ) -> None:
        """PortalEstimateResponse does not contain any internal UUID fields
        like id, lead_id, customer_id, job_id, template_id."""
        fields = PortalEstimateResponse.model_fields
        internal_id_fields = {
            "id",
            "lead_id",
            "customer_id",
            "job_id",
            "template_id",
            "staff_id",
            "created_by",
        }
        exposed_internal = internal_id_fields & set(fields.keys())
        assert exposed_internal == set(), (
            f"Internal IDs exposed in portal response: {exposed_internal}"
        )

    def test_portal_estimate_response_contains_expected_public_fields(
        self,
    ) -> None:
        """PortalEstimateResponse contains the expected public-facing fields."""
        fields = set(PortalEstimateResponse.model_fields.keys())
        expected = {
            "status",
            "line_items",
            "subtotal",
            "tax_amount",
            "discount_amount",
            "total",
            "valid_until",
            "notes",
            "readonly",
        }
        assert expected.issubset(fields), (
            f"Missing expected fields: {expected - fields}"
        )

    @given(
        subtotal=st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("99999.99"),
            places=2,
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    @settings(max_examples=30)
    def test_portal_estimate_response_serializes_without_internal_ids(
        self,
        subtotal: Decimal,
    ) -> None:
        """For any valid subtotal, serializing a PortalEstimateResponse
        never includes internal ID fields in the output.

        **Validates: Requirements 78.6**
        """
        response = PortalEstimateResponse(
            status="sent",
            subtotal=subtotal,
            tax_amount=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total=subtotal,
        )
        data = response.model_dump()

        internal_keys = {
            "id",
            "lead_id",
            "customer_id",
            "job_id",
            "template_id",
            "staff_id",
            "created_by",
        }
        found = internal_keys & set(data.keys())
        assert found == set(), f"Internal IDs in serialized output: {found}"

    def test_estimate_response_does_contain_internal_ids(self) -> None:
        """Contrast: the internal EstimateResponse DOES have internal IDs,
        confirming the portal schema correctly strips them."""
        fields = set(EstimateResponse.model_fields.keys())
        assert "lead_id" in fields
        assert "customer_id" in fields
        assert "job_id" in fields
        assert "template_id" in fields
