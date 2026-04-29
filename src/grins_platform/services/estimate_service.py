"""Estimate service for estimate lifecycle management.

Handles creation, templates, sending, portal approval/rejection,
follow-ups, auto-routing, and promotions.

Validates: CRM Gap Closure Req 16, 17, 32, 48, 51, 78
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Literal

from grins_platform.exceptions import (
    EstimateAlreadyApprovedError,
    EstimateNotFoundError,
    EstimateTemplateNotFoundError,
    EstimateTokenExpiredError,
    InvalidPromotionCodeError,
)
from grins_platform.log_config import LoggerMixin
from grins_platform.models.enums import (
    ActionTag,
    EstimateStatus,
    FollowUpStatus,
)
from grins_platform.schemas.estimate import (
    EstimateCreate,
    EstimateResponse,
    EstimateSendResponse,
)

if TYPE_CHECKING:
    from uuid import UUID

    from grins_platform.models.estimate import Estimate
    from grins_platform.repositories.estimate_repository import EstimateRepository
    from grins_platform.services.email_service import EmailService
    from grins_platform.services.lead_service import LeadService
    from grins_platform.services.sales_pipeline_service import SalesPipelineService
    from grins_platform.services.sms_service import SMSService

# Follow-up schedule: days after sending
FOLLOW_UP_DAYS = [3, 7, 14, 21]

# Portal token validity in days
TOKEN_VALIDITY_DAYS = 60

# Auto-routing threshold in hours
AUTO_ROUTE_HOURS = 4

# Hardcoded promotion codes for MVP (can be moved to DB later)
VALID_PROMOTIONS: dict[str, Decimal] = {
    "SAVE10": Decimal("0.10"),
    "SAVE15": Decimal("0.15"),
    "SAVE20": Decimal("0.20"),
    "SPRING25": Decimal("0.25"),
    "WELCOME5": Decimal("0.05"),
}


class EstimateService(LoggerMixin):
    """Service for estimate lifecycle management.

    Handles creation, templates, sending via portal, customer
    approval/rejection, follow-up scheduling, auto-routing of
    unapproved estimates, and promotional discounts.

    Validates: CRM Gap Closure Req 16, 17, 32, 48, 51, 78
    """

    DOMAIN = "estimate"

    def __init__(
        self,
        estimate_repository: EstimateRepository,
        portal_base_url: str,
        lead_service: LeadService | None = None,
        sms_service: SMSService | None = None,
        email_service: EmailService | None = None,
        sales_pipeline_service: SalesPipelineService | None = None,
    ) -> None:
        """Initialize service with dependencies.

        Args:
            estimate_repository: Repository for estimate DB operations.
            portal_base_url: Base URL origin for customer portal links
                (path is appended by the service — must be the origin
                only, e.g. ``http://localhost:5173``).
            lead_service: Optional LeadService for cross-service tag updates.
            sms_service: Optional SMSService for sending portal links.
            email_service: Optional EmailService for sending portal links.
            sales_pipeline_service: Optional SalesPipelineService for
                writing approve/reject breadcrumbs to the active
                SalesEntry (Q-A correlation).
        """
        super().__init__()
        self.repo = estimate_repository
        self.lead_service = lead_service
        self.sms_service = sms_service
        self.email_service = email_service
        self.sales_pipeline_service = sales_pipeline_service
        self.portal_base_url = portal_base_url

    # =========================================================================
    # Estimate Creation
    # =========================================================================

    async def create_estimate(
        self,
        data: EstimateCreate,
        created_by: UUID,
    ) -> EstimateResponse:
        """Create an estimate with line items and optional tiers.

        Calculates subtotal/tax/discount/total from line items.
        Generates a customer_token (UUID v4) and sets token_expires_at
        to 60 days from now.

        Args:
            data: Estimate creation data.
            created_by: UUID of the staff member creating the estimate.

        Returns:
            EstimateResponse with the created estimate.

        Validates: Requirements 48.4, 48.5, 48.6, 48.7, 78.1
        """
        self.log_started(
            "create_estimate",
            created_by=str(created_by),
            lead_id=str(data.lead_id) if data.lead_id else None,
            customer_id=str(data.customer_id) if data.customer_id else None,
        )

        # Calculate totals from line items
        subtotal = self._calculate_subtotal(data.line_items)
        tax_amount = data.tax_amount if data.tax_amount else Decimal(0)
        discount_amount = data.discount_amount if data.discount_amount else Decimal(0)
        total = subtotal + tax_amount - discount_amount

        # Generate portal token
        customer_token = uuid.uuid4()
        token_expires_at = datetime.now(tz=timezone.utc) + timedelta(
            days=TOKEN_VALIDITY_DAYS,
        )

        now = datetime.now(tz=timezone.utc)
        estimate = await self.repo.create(
            lead_id=data.lead_id,
            customer_id=data.customer_id,
            job_id=data.job_id,
            template_id=data.template_id,
            status=EstimateStatus.DRAFT.value,
            line_items=data.line_items,
            options=data.options,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=discount_amount,
            total=total,
            promotion_code=data.promotion_code,
            valid_until=data.valid_until or (now + timedelta(days=60)),
            notes=data.notes,
            customer_token=customer_token,
            token_expires_at=token_expires_at,
        )

        self.log_completed(
            "create_estimate",
            estimate_id=str(estimate.id),
            total=str(total),
        )
        response: EstimateResponse = EstimateResponse.model_validate(estimate)
        return response

    # =========================================================================
    # Template-Based Creation
    # =========================================================================

    async def create_from_template(
        self,
        template_id: UUID,
        overrides: dict[str, Any],
        created_by: UUID,
    ) -> EstimateResponse:
        """Create an estimate from a template with optional overrides.

        Clones the template's line_items and applies any overrides
        provided by the caller.

        Args:
            template_id: UUID of the estimate template.
            overrides: Dict of fields to override from the template.
            created_by: UUID of the staff member.

        Returns:
            EstimateResponse with the created estimate.

        Raises:
            EstimateTemplateNotFoundError: If template not found.

        Validates: Requirements 17.3, 17.4, 17.5
        """
        self.log_started(
            "create_from_template",
            template_id=str(template_id),
            created_by=str(created_by),
        )

        template = await self.repo.get_template_by_id(template_id)
        if not template:
            self.log_rejected(
                "create_from_template",
                reason="template_not_found",
            )
            raise EstimateTemplateNotFoundError(template_id)

        # Build creation data from template + overrides
        line_items = overrides.get("line_items", template.line_items)
        create_data = EstimateCreate(
            lead_id=overrides.get("lead_id"),
            customer_id=overrides.get("customer_id"),
            job_id=overrides.get("job_id"),
            template_id=template_id,
            line_items=line_items,
            options=overrides.get("options"),
            tax_amount=overrides.get("tax_amount", Decimal(0)),
            discount_amount=overrides.get("discount_amount", Decimal(0)),
            notes=overrides.get("notes", template.terms),
        )

        result = await self.create_estimate(create_data, created_by)

        self.log_completed(
            "create_from_template",
            estimate_id=str(result.id),
            template_id=str(template_id),
        )
        return result

    # =========================================================================
    # Sending
    # =========================================================================

    async def send_estimate(
        self,
        estimate_id: UUID,
    ) -> EstimateSendResponse:
        """Send an estimate to the customer via SMS and email.

        Sets status to SENT, generates portal link, sends via available
        channels, and schedules follow-ups at Day 3, 7, 14, 21.

        Args:
            estimate_id: UUID of the estimate to send.

        Returns:
            EstimateSendResponse with portal URL and channels used.

        Raises:
            EstimateNotFoundError: If estimate not found.

        Validates: Requirements 48.4, 48.5, 51.2, 51.3, 51.4
        """
        self.log_started("send_estimate", estimate_id=str(estimate_id))

        estimate = await self.repo.get_by_id(estimate_id)
        if not estimate:
            self.log_rejected("send_estimate", reason="not_found")
            raise EstimateNotFoundError(estimate_id)

        # Update status to SENT
        _ = await self.repo.update(
            estimate_id,
            status=EstimateStatus.SENT.value,
        )

        # Build portal URL
        portal_url = (
            f"{self.portal_base_url}/portal/estimates/{estimate.customer_token}"
        )

        # Send via available channels
        sent_via: list[str] = []

        # SMS
        if self.sms_service and estimate.customer:
            phone = getattr(estimate.customer, "phone", None)
            if phone:
                try:
                    message = (
                        f"Your estimate from Grins Irrigation is ready! "
                        f"Review it here: {portal_url}"
                    )
                    _ = await self.sms_service.send_automated_message(
                        phone=phone,
                        message=message,
                        message_type="estimate_sent",
                    )
                    sent_via.append("sms")
                except Exception as e:
                    self.log_failed(
                        "send_estimate_sms",
                        error=e,
                        estimate_id=str(estimate_id),
                    )

        # Email
        if self.email_service and estimate.customer:
            email = getattr(estimate.customer, "email", None)
            if email:
                try:
                    result = self.email_service.send_estimate_email(
                        customer=estimate.customer,
                        estimate=estimate,
                        portal_url=portal_url,
                    )
                    if result.get("sent"):
                        sent_via.append("email")
                except Exception as e:
                    self.log_failed(
                        "send_estimate_email",
                        error=e,
                        estimate_id=str(estimate_id),
                    )

        # Also try lead contact info if no customer
        if not sent_via and estimate.lead:
            lead = estimate.lead
            if self.sms_service and getattr(lead, "phone", None):
                try:
                    message = (
                        f"Your estimate from Grins Irrigation is ready! "
                        f"Review it here: {portal_url}"
                    )
                    _ = await self.sms_service.send_automated_message(
                        phone=lead.phone,
                        message=message,
                        message_type="estimate_sent",
                    )
                    sent_via.append("sms")
                except Exception as e:
                    self.log_failed(
                        "send_estimate_sms_lead",
                        error=e,
                        estimate_id=str(estimate_id),
                    )
            if self.email_service and getattr(lead, "email", None):
                try:
                    result = self.email_service.send_estimate_email(
                        customer=lead,
                        estimate=estimate,
                        portal_url=portal_url,
                    )
                    if result.get("sent"):
                        sent_via.append("email")
                except Exception as e:
                    self.log_failed(
                        "send_estimate_email_lead",
                        error=e,
                        estimate_id=str(estimate_id),
                    )

        # Schedule follow-ups
        await self._schedule_follow_ups(estimate)

        self.log_completed(
            "send_estimate",
            estimate_id=str(estimate_id),
            sent_via=sent_via,
        )

        return EstimateSendResponse(
            estimate_id=estimate.id,
            portal_url=portal_url,
            sent_via=sent_via,
        )

    # =========================================================================
    # Portal Approval / Rejection
    # =========================================================================

    async def approve_via_portal(
        self,
        token: UUID,
        ip_address: str,
        user_agent: str,
    ) -> EstimateResponse:
        """Record customer approval via the portal.

        Records timestamp, IP, user_agent. Sets token_readonly=True.
        Updates lead tag to ESTIMATE_APPROVED. Cancels remaining
        follow-ups.

        Args:
            token: Customer portal token.
            ip_address: Client IP address.
            user_agent: Client user agent string.

        Returns:
            EstimateResponse with the approved estimate.

        Raises:
            EstimateNotFoundError: If token not found.
            EstimateTokenExpiredError: If token is expired.
            EstimateAlreadyApprovedError: If already decided.

        Validates: Requirements 16.1, 16.2, 16.5, 78.1, 78.2, 78.3, 78.4
        """
        self.log_started("approve_via_portal")

        estimate = await self._validate_portal_token(token)

        # Check not already decided
        if estimate.approved_at or estimate.rejected_at:
            self.log_rejected(
                "approve_via_portal",
                reason="already_decided",
            )
            raise EstimateAlreadyApprovedError(estimate.id)

        now = datetime.now(tz=timezone.utc)

        # Record approval
        updated = await self.repo.update(
            estimate.id,
            status=EstimateStatus.APPROVED.value,
            approved_at=now,
            approved_ip=ip_address,
            approved_user_agent=user_agent,
            token_readonly=True,
        )

        # Cancel remaining follow-ups
        cancelled = await self.repo.cancel_follow_ups_for_estimate(estimate.id)
        self.logger.info(
            "estimate.follow_ups.cancelled_on_approval",
            estimate_id=str(estimate.id),
            cancelled_count=cancelled,
        )

        # Update lead tag to ESTIMATE_APPROVED
        if estimate.lead_id and self.lead_service:
            try:
                _ = await self.lead_service.update_action_tags(
                    estimate.lead_id,
                    add_tags=[ActionTag.ESTIMATE_APPROVED],
                    remove_tags=[ActionTag.ESTIMATE_PENDING],
                )
            except Exception as e:
                self.log_failed(
                    "approve_via_portal_lead_update",
                    error=e,
                    lead_id=str(estimate.lead_id),
                )

        await self._notify_internal_decision(updated, "approved")
        await self._correlate_to_sales_entry(updated, "approved")

        self.log_completed(
            "approve_via_portal",
            estimate_id=str(estimate.id),
        )
        response: EstimateResponse = EstimateResponse.model_validate(updated)
        return response

    async def reject_via_portal(
        self,
        token: UUID,
        reason: str | None = None,
    ) -> EstimateResponse:
        """Record customer rejection via the portal.

        Records rejection timestamp and optional reason.
        Cancels remaining follow-ups.

        Args:
            token: Customer portal token.
            reason: Optional rejection reason.

        Returns:
            EstimateResponse with the rejected estimate.

        Raises:
            EstimateNotFoundError: If token not found.
            EstimateTokenExpiredError: If token is expired.
            EstimateAlreadyApprovedError: If already decided.

        Validates: Requirements 16.3, 78.1, 78.2, 78.5
        """
        self.log_started("reject_via_portal")

        estimate = await self._validate_portal_token(token)

        if estimate.approved_at or estimate.rejected_at:
            self.log_rejected(
                "reject_via_portal",
                reason="already_decided",
            )
            raise EstimateAlreadyApprovedError(estimate.id)

        now = datetime.now(tz=timezone.utc)

        updated = await self.repo.update(
            estimate.id,
            status=EstimateStatus.REJECTED.value,
            rejected_at=now,
            rejected_reason=reason,
            token_readonly=True,
        )

        # Cancel remaining follow-ups
        cancelled = await self.repo.cancel_follow_ups_for_estimate(estimate.id)
        self.logger.info(
            "estimate.follow_ups.cancelled_on_rejection",
            estimate_id=str(estimate.id),
            cancelled_count=cancelled,
        )

        # Update lead tag if applicable
        if estimate.lead_id and self.lead_service:
            try:
                _ = await self.lead_service.update_action_tags(
                    estimate.lead_id,
                    add_tags=[ActionTag.ESTIMATE_REJECTED],
                    remove_tags=[ActionTag.ESTIMATE_PENDING],
                )
            except Exception as e:
                self.log_failed(
                    "reject_via_portal_lead_update",
                    error=e,
                    lead_id=str(estimate.lead_id),
                )

        await self._notify_internal_decision(updated, "rejected")
        await self._correlate_to_sales_entry(updated, "rejected", reason=reason)

        self.log_completed(
            "reject_via_portal",
            estimate_id=str(estimate.id),
            reason=reason,
        )
        response: EstimateResponse = EstimateResponse.model_validate(updated)
        return response

    # =========================================================================
    # Internal Notifications + Sales Pipeline Correlation
    # =========================================================================

    async def _notify_internal_decision(
        self,
        estimate: Estimate | None,
        decision: Literal["approved", "rejected"],
    ) -> None:
        """Fire-and-log internal staff notification. Never raises.

        Failures (vendor outage, no recipients configured) are logged
        but never undo the customer-side decision.
        """
        if estimate is None:
            return
        recipient_email = os.getenv("INTERNAL_NOTIFICATION_EMAIL", "").strip()
        recipient_phone = os.getenv("INTERNAL_NOTIFICATION_PHONE", "").strip()
        customer_name = self._resolve_customer_name(estimate)
        total = str(getattr(estimate, "total", "0.00"))
        rejection_reason = (
            getattr(estimate, "rejected_reason", None)
            if decision == "rejected"
            else None
        )

        if recipient_email and self.email_service:
            try:
                self.email_service.send_internal_estimate_decision_email(
                    to_email=recipient_email,
                    decision=decision,
                    customer_name=customer_name,
                    total=total,
                    estimate_id=estimate.id,
                    rejection_reason=rejection_reason,
                )
            except Exception as e:
                self.log_failed(
                    "notify_internal_decision_email",
                    error=e,
                    estimate_id=str(estimate.id),
                )

        if recipient_phone and self.sms_service:
            subject_word = decision.upper()
            sms_text = (
                f"Estimate {subject_word} for {customer_name}. "
                f"Total ${total}. Open admin to action."
            )
            try:
                _ = await self.sms_service.send_automated_message(
                    phone=recipient_phone,
                    message=sms_text,
                    message_type="internal_estimate_decision",
                )
            except Exception as e:
                self.log_failed(
                    "notify_internal_decision_sms",
                    error=e,
                    estimate_id=str(estimate.id),
                )

    async def _correlate_to_sales_entry(
        self,
        estimate: Estimate | None,
        decision: Literal["approved", "rejected"],
        *,
        reason: str | None = None,
    ) -> None:
        """Best-effort breadcrumb on the active SalesEntry. Never raises."""
        if estimate is None or not self.sales_pipeline_service:
            return
        try:
            _ = await self.sales_pipeline_service.record_estimate_decision_breadcrumb(
                self.repo.session,
                estimate,
                decision,
                reason=reason,
            )
        except Exception as e:
            self.log_failed(
                "correlate_to_sales_entry",
                error=e,
                estimate_id=str(estimate.id),
            )

    @staticmethod
    def _resolve_customer_name(estimate: Estimate) -> str:
        """Return a human-readable name for the estimate's recipient."""
        customer = getattr(estimate, "customer", None)
        if customer is not None:
            full_name = getattr(customer, "full_name", None)
            if full_name:
                return str(full_name)
            first = getattr(customer, "first_name", "") or ""
            last = getattr(customer, "last_name", "") or ""
            joined = f"{first} {last}".strip()
            if joined:
                return joined
        lead = getattr(estimate, "lead", None)
        if lead is not None:
            first = getattr(lead, "first_name", "") or ""
            last = getattr(lead, "last_name", "") or ""
            joined = f"{first} {last}".strip()
            if joined:
                return joined
        return "a customer"

    # =========================================================================
    # Background Jobs
    # =========================================================================

    async def check_unapproved_estimates(self) -> int:
        """Background job: find estimates >4hrs old without approval.

        Creates leads with ESTIMATE_PENDING tag via LeadService for
        unapproved estimates that have been sent but not acted upon.

        Returns:
            Number of estimates routed to leads.

        Validates: Requirements 32.3, 32.4, 32.7
        """
        self.log_started("check_unapproved_estimates")

        estimates = await self.repo.find_unapproved_older_than(AUTO_ROUTE_HOURS)
        routed = 0

        for estimate in estimates:
            if not estimate.customer_id:
                self.logger.info(
                    "estimate.auto_route.skipped",
                    estimate_id=str(estimate.id),
                    reason="no_customer_id",
                )
                continue

            if self.lead_service:
                try:
                    _ = await self.lead_service.create_lead_from_estimate(
                        customer_id=estimate.customer_id,
                        estimate_id=estimate.id,
                    )
                    routed += 1
                    self.logger.info(
                        "estimate.auto_route.created",
                        estimate_id=str(estimate.id),
                        customer_id=str(estimate.customer_id),
                    )
                except Exception as e:
                    self.log_failed(
                        "check_unapproved_estimates_route",
                        error=e,
                        estimate_id=str(estimate.id),
                    )

        self.log_completed(
            "check_unapproved_estimates",
            total_found=len(estimates),
            routed=routed,
        )
        return routed

    async def process_follow_ups(self) -> int:
        """Background job: send due follow-ups.

        Finds all scheduled follow-ups with scheduled_at in the past
        and sends them via SMS/email.

        Returns:
            Number of follow-ups sent.

        Validates: Requirements 51.2, 51.3, 51.4, 51.5
        """
        self.log_started("process_follow_ups")

        pending = await self.repo.get_pending_follow_ups()
        sent_count = 0

        for follow_up in pending:
            estimate = await self.repo.get_by_id(follow_up.estimate_id)
            if not estimate:
                self.logger.warning(
                    "estimate.follow_up.orphaned",
                    follow_up_id=str(follow_up.id),
                    estimate_id=str(follow_up.estimate_id),
                )
                continue

            # Skip if estimate already decided
            if estimate.approved_at or estimate.rejected_at:
                _ = await self.repo.cancel_follow_ups_for_estimate(estimate.id)
                continue

            # Build portal URL
            portal_url = (
                f"{self.portal_base_url}/portal/estimates/{estimate.customer_token}"
            )

            message = follow_up.message or (
                f"Reminder: Your estimate from Grins Irrigation is "
                f"waiting for your review. View it here: {portal_url}"
            )

            if follow_up.promotion_code:
                message += f" Use code {follow_up.promotion_code} for a discount!"

            # Attempt to send
            success = False
            phone = self._get_contact_phone(estimate)

            if self.sms_service and phone:
                try:
                    _ = await self.sms_service.send_automated_message(
                        phone=phone,
                        message=message,
                        message_type="estimate_sent",
                    )
                    success = True
                except Exception as e:
                    self.log_failed(
                        "process_follow_up_sms",
                        error=e,
                        follow_up_id=str(follow_up.id),
                    )

            if success:
                # Mark as sent
                now = datetime.now(tz=timezone.utc)
                follow_up.status = FollowUpStatus.SENT.value
                follow_up.sent_at = now
                await self.repo.session.flush()
                sent_count += 1
                self.logger.info(
                    "estimate.follow_up.sent",
                    follow_up_id=str(follow_up.id),
                    estimate_id=str(estimate.id),
                    follow_up_number=follow_up.follow_up_number,
                )
            else:
                # Mark as skipped if no channel available
                follow_up.status = FollowUpStatus.SKIPPED.value
                await self.repo.session.flush()
                self.logger.warning(
                    "estimate.follow_up.skipped",
                    follow_up_id=str(follow_up.id),
                    reason="no_channel_available",
                )

        self.log_completed(
            "process_follow_ups",
            total_pending=len(pending),
            sent=sent_count,
        )
        return sent_count

    # =========================================================================
    # Promotions
    # =========================================================================

    async def apply_promotion(
        self,
        estimate_id: UUID,
        code: str,
    ) -> EstimateResponse:
        """Validate a promotion code and calculate discounted total.

        Args:
            estimate_id: UUID of the estimate.
            code: Promotion code string.

        Returns:
            EstimateResponse with updated discount and total.

        Raises:
            EstimateNotFoundError: If estimate not found.
            InvalidPromotionCodeError: If code is invalid.

        Validates: Requirements 48.6, 48.7
        """
        self.log_started(
            "apply_promotion",
            estimate_id=str(estimate_id),
            code=code,
        )

        estimate = await self.repo.get_by_id(estimate_id)
        if not estimate:
            self.log_rejected("apply_promotion", reason="estimate_not_found")
            raise EstimateNotFoundError(estimate_id)

        code_upper = code.strip().upper()
        discount_rate = VALID_PROMOTIONS.get(code_upper)
        if discount_rate is None:
            self.log_rejected(
                "apply_promotion",
                reason="invalid_code",
            )
            raise InvalidPromotionCodeError(code)

        # Calculate discount from subtotal
        discount_amount = estimate.subtotal * discount_rate
        new_total = estimate.subtotal + estimate.tax_amount - discount_amount

        updated = await self.repo.update(
            estimate_id,
            promotion_code=code_upper,
            discount_amount=discount_amount,
            total=new_total,
        )

        self.log_completed(
            "apply_promotion",
            estimate_id=str(estimate_id),
            discount_rate=str(discount_rate),
            discount_amount=str(discount_amount),
            new_total=str(new_total),
        )
        response: EstimateResponse = EstimateResponse.model_validate(updated)
        return response

    # =========================================================================
    # Portal Token Access (public)
    # =========================================================================

    async def get_by_portal_token(self, token: UUID) -> Estimate:
        """Retrieve an estimate by its portal token.

        Validates the token exists and is not expired.

        Args:
            token: Customer portal token (UUID v4).

        Returns:
            The Estimate model instance.

        Raises:
            EstimateNotFoundError: If token not found.
            EstimateTokenExpiredError: If token is expired.

        Validates: Requirements 16.1, 78.1, 78.2
        """
        return await self._validate_portal_token(token)

    # =========================================================================
    # Private Helpers
    # =========================================================================

    async def _validate_portal_token(self, token: UUID) -> Estimate:
        """Validate a portal token and return the estimate.

        Args:
            token: Customer portal token.

        Returns:
            The Estimate model instance.

        Raises:
            EstimateNotFoundError: If token not found.
            EstimateTokenExpiredError: If token is expired.
        """
        estimate = await self.repo.get_by_token(token)
        if not estimate:
            raise EstimateNotFoundError(str(token))

        # Check expiration
        if estimate.token_expires_at:
            now = datetime.now(tz=timezone.utc)
            if now > estimate.token_expires_at:
                raise EstimateTokenExpiredError(token)

        return estimate

    async def _schedule_follow_ups(self, estimate: Estimate) -> None:
        """Schedule follow-ups at Day 3, 7, 14, 21 after sending.

        Args:
            estimate: The estimate to schedule follow-ups for.

        Validates: Requirements 51.2, 51.3, 51.4
        """
        now = datetime.now(tz=timezone.utc)

        for i, days in enumerate(FOLLOW_UP_DAYS, start=1):
            scheduled_at = now + timedelta(days=days)

            # Later follow-ups get a promotion code to incentivize
            promo = None
            if i >= 3:  # Day 14+ gets a promo
                promo = "SAVE10"

            _ = await self.repo.create_follow_up(
                estimate_id=estimate.id,
                follow_up_number=i,
                scheduled_at=scheduled_at,
                channel="sms",
                message=None,  # Default message used at send time
                promotion_code=promo,
                status=FollowUpStatus.SCHEDULED.value,
            )

        self.logger.info(
            "estimate.follow_ups.scheduled",
            estimate_id=str(estimate.id),
            count=len(FOLLOW_UP_DAYS),
        )

    @staticmethod
    def _calculate_subtotal(
        line_items: list[dict[str, Any]] | None,
    ) -> Decimal:
        """Calculate subtotal from line items.

        Each line item should have 'unit_price' and 'quantity' fields.

        Args:
            line_items: List of line item dicts.

        Returns:
            Calculated subtotal as Decimal.
        """
        if not line_items:
            return Decimal(0)

        total = Decimal(0)
        for item in line_items:
            unit_price = Decimal(str(item.get("unit_price", 0)))
            quantity = Decimal(str(item.get("quantity", 1)))
            total += unit_price * quantity

        return total

    @staticmethod
    def _get_contact_phone(estimate: Estimate) -> str | None:
        """Get the best contact phone for an estimate.

        Checks customer first, then lead.

        Args:
            estimate: The estimate instance.

        Returns:
            Phone number string or None.
        """
        if estimate.customer:
            phone = getattr(estimate.customer, "phone", None)
            if phone:
                return str(phone)

        if estimate.lead:
            phone = getattr(estimate.lead, "phone", None)
            if phone:
                return str(phone)

        return None
