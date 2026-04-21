"""
Enum types for Grin's Irrigation Platform models.

This module defines all enum types used across the platform,
ensuring type safety and consistent values across the application.

Phase 1 (Customer Management): CustomerStatus, LeadSource, SystemType, PropertyType
Phase 2 (Field Operations): ServiceCategory, PricingModel, JobCategory, JobStatus,
                           JobSource, StaffRole, SkillLevel
Phase 8 (Authentication): UserRole
Phase 8 (Invoice Management): InvoiceStatus, PaymentMethod

Validates: Requirements 1.12, 2.3, 2.4 (Phase 1)
Validates: Requirements 1.2, 1.3, 4.1, 8.2, 8.3 (Phase 2)
Validates: Requirement 17.1 (Phase 8 - Authentication)
Validates: Requirements 8.1-8.10, 9.2 (Phase 8 - Invoice)
"""

from enum import Enum

# =============================================================================
# Phase 1: Customer Management Enums
# =============================================================================


class CustomerStatus(str, Enum):
    """Customer status enumeration.

    Validates: Requirement 1.12
    """

    ACTIVE = "active"
    INACTIVE = "inactive"


class LeadSource(str, Enum):
    """Lead source enumeration for marketing attribution.

    Validates: Requirement 1.9
    """

    WEBSITE = "website"
    GOOGLE = "google"
    REFERRAL = "referral"
    AD = "ad"
    WORD_OF_MOUTH = "word_of_mouth"


class SystemType(str, Enum):
    """Irrigation system type enumeration.

    Validates: Requirement 2.3
    """

    STANDARD = "standard"
    LAKE_PUMP = "lake_pump"


class PropertyType(str, Enum):
    """Property type enumeration.

    Validates: Requirement 2.4
    """

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"


# =============================================================================
# Phase 2: Field Operations Enums
# =============================================================================


class ServiceCategory(str, Enum):
    """Service category enumeration for service offerings.

    Validates: Requirement 1.2
    """

    SEASONAL = "seasonal"
    REPAIR = "repair"
    INSTALLATION = "installation"
    DIAGNOSTIC = "diagnostic"
    LANDSCAPING = "landscaping"


class PricingModel(str, Enum):
    """Pricing model enumeration for service offerings.

    Validates: Requirement 1.3
    """

    FLAT = "flat"
    ZONE_BASED = "zone_based"
    HOURLY = "hourly"
    CUSTOM = "custom"


class JobCategory(str, Enum):
    """Job category enumeration for auto-categorization.

    Validates: Requirement 3.1-3.5
    """

    READY_TO_SCHEDULE = "ready_to_schedule"
    REQUIRES_ESTIMATE = "requires_estimate"


class JobStatus(str, Enum):
    """Job status enumeration for workflow management.

    Validates: Requirement 4.1, 5.1
    """

    TO_BE_SCHEDULED = "to_be_scheduled"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class JobSource(str, Enum):
    """Job source enumeration for lead attribution.

    Validates: Requirement 2.11
    """

    WEBSITE = "website"
    GOOGLE = "google"
    REFERRAL = "referral"
    PHONE = "phone"
    PARTNER = "partner"


class StaffRole(str, Enum):
    """Staff role enumeration.

    Validates: Requirement 8.2
    """

    TECH = "tech"
    SALES = "sales"
    ADMIN = "admin"


class SkillLevel(str, Enum):
    """Staff skill level enumeration.

    Validates: Requirement 8.3
    """

    JUNIOR = "junior"
    SENIOR = "senior"
    LEAD = "lead"


# =============================================================================
# Phase 3: Admin Dashboard Enums
# =============================================================================


class AppointmentStatus(str, Enum):
    """Appointment status enumeration.

    Validates: Admin Dashboard Requirement 1.3, CRM Gap Closure Req 79, Req 8.1
    """

    PENDING = "pending"
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    EN_ROUTE = "en_route"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


# =============================================================================
# Phase 8: Authentication Enums
# =============================================================================


class UserRole(str, Enum):
    """User role enumeration for role-based access control.

    Validates: Requirement 17.1
    """

    ADMIN = "admin"
    MANAGER = "manager"
    TECH = "tech"


# =============================================================================
# Phase 8: Invoice Management Enums
# =============================================================================


class InvoiceStatus(str, Enum):
    """Invoice status enumeration for invoice workflow management.

    Validates: Requirements 8.1-8.10
    """

    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    PAID = "paid"
    PARTIAL = "partial"
    OVERDUE = "overdue"
    LIEN_WARNING = "lien_warning"
    LIEN_FILED = "lien_filed"
    CANCELLED = "cancelled"


class PaymentMethod(str, Enum):
    """Payment method enumeration for invoice payments.

    Validates: Requirement 9.2

    H-4 (bughunt 2026-04-16): extended with ``credit_card``, ``ach``, and
    ``other`` to match the spec vocabulary. ``stripe`` is retained for
    existing rows that were persisted before the change; new UI pickers
    omit ``stripe`` in favor of ``credit_card``.
    """

    CASH = "cash"
    CHECK = "check"
    VENMO = "venmo"
    ZELLE = "zelle"
    STRIPE = "stripe"  # retained for legacy rows — not offered in new UI
    CREDIT_CARD = "credit_card"
    ACH = "ach"
    OTHER = "other"


# =============================================================================
# Lead Capture Enums
# =============================================================================


class LeadStatus(str, Enum):
    """Lead status enumeration for pipeline tracking.

    Validates: Lead Capture Requirement 4.4
    """

    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    CONVERTED = "converted"
    LOST = "lost"
    SPAM = "spam"


class LeadSituation(str, Enum):
    """Lead situation enumeration mapping to form dropdown options.

    Validates: Lead Capture Requirement 4.5
    """

    NEW_SYSTEM = "new_system"
    UPGRADE = "upgrade"
    REPAIR = "repair"
    EXPLORING = "exploring"
    WINTERIZATION = "winterization"
    SEASONAL_MAINTENANCE = "seasonal_maintenance"


VALID_LEAD_STATUS_TRANSITIONS: dict[
    LeadStatus,
    set[LeadStatus],
] = {
    LeadStatus.NEW: {
        LeadStatus.CONTACTED,
        LeadStatus.QUALIFIED,
        LeadStatus.LOST,
        LeadStatus.SPAM,
    },
    LeadStatus.CONTACTED: {
        LeadStatus.QUALIFIED,
        LeadStatus.LOST,
        LeadStatus.SPAM,
    },
    LeadStatus.QUALIFIED: {
        LeadStatus.CONVERTED,
        LeadStatus.LOST,
    },
    LeadStatus.CONVERTED: set(),  # terminal
    LeadStatus.LOST: {LeadStatus.NEW},  # re-engagement
    LeadStatus.SPAM: set(),  # terminal
}


# =============================================================================
# Service Package Purchases Enums
# =============================================================================


class AgreementStatus(str, Enum):
    """Service agreement lifecycle status.

    Validates: Requirement 2.1, 5.1
    """

    PENDING = "pending"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    PAUSED = "paused"
    PENDING_RENEWAL = "pending_renewal"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AgreementPaymentStatus(str, Enum):
    """Payment status for service agreements.

    Validates: Requirement 2.1
    """

    CURRENT = "current"
    PAST_DUE = "past_due"
    FAILED = "failed"


class PackageType(str, Enum):
    """Package type for service agreement tiers.

    Validates: Requirement 1.1
    """

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"


class BillingFrequency(str, Enum):
    """Billing frequency for service agreement tiers.

    Validates: Requirement 1.1
    """

    ANNUAL = "annual"


class DisclosureType(str, Enum):
    """Disclosure record types for MN auto-renewal compliance.

    Validates: Requirement 33.1
    """

    PRE_SALE = "pre_sale"
    CONFIRMATION = "confirmation"
    RENEWAL_NOTICE = "renewal_notice"
    ANNUAL_NOTICE = "annual_notice"
    MATERIAL_CHANGE = "material_change"
    CANCELLATION_CONF = "cancellation_conf"


class WebhookProcessingStatus(str, Enum):
    """Stripe webhook event processing status.

    Validates: Requirement 7.1
    """

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EmailType(str, Enum):
    """Email classification for CAN-SPAM compliance.

    Validates: Requirement 39B.1
    """

    TRANSACTIONAL = "transactional"
    COMMERCIAL = "commercial"


class IntakeTag(str, Enum):
    """Lead intake routing disposition.

    Validates: Requirement 47.1
    """

    SCHEDULE = "schedule"
    FOLLOW_UP = "follow_up"


class LeadSourceExtended(str, Enum):
    """Extended lead source channels for attribution.

    Validates: Requirement 44.1
    """

    WEBSITE = "website"
    GOOGLE_FORM = "google_form"
    PHONE_CALL = "phone_call"
    TEXT_MESSAGE = "text_message"
    GOOGLE_AD = "google_ad"
    SOCIAL_MEDIA = "social_media"
    QR_CODE = "qr_code"
    EMAIL_CAMPAIGN = "email_campaign"
    TEXT_CAMPAIGN = "text_campaign"
    REFERRAL = "referral"
    YARD_SIGN = "yard_sign"
    OTHER = "other"


# =============================================================================
# CRM Gap Closure Enums
# =============================================================================


class CommunicationChannel(str, Enum):
    """Communication channel for inbound/outbound messages.

    Validates: CRM Gap Closure Req 4.4
    """

    SMS = "sms"
    EMAIL = "email"
    PHONE = "phone"
    VOICEMAIL = "voicemail"
    CHAT = "chat"


class CommunicationDirection(str, Enum):
    """Direction of a communication record.

    Validates: CRM Gap Closure Req 4.4
    """

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class AttachmentType(str, Enum):
    """Type classification for lead attachments.

    Validates: CRM Gap Closure Req 15.1
    """

    ESTIMATE = "estimate"
    CONTRACT = "contract"
    PHOTO = "photo"
    DOCUMENT = "document"
    OTHER = "other"


class EstimateStatus(str, Enum):
    """Estimate lifecycle status.

    Validates: CRM Gap Closure Req 48.1
    """

    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ActionTag(str, Enum):
    """Action tags for lead pipeline tracking.

    Validates: CRM Gap Closure Req 13.1
    """

    NEEDS_CONTACT = "needs_contact"
    NEEDS_ESTIMATE = "needs_estimate"
    ESTIMATE_PENDING = "estimate_pending"
    ESTIMATE_APPROVED = "estimate_approved"
    ESTIMATE_REJECTED = "estimate_rejected"


class ExpenseCategory(str, Enum):
    """Expense category for accounting.

    Validates: CRM Gap Closure Req 53.1
    """

    MATERIALS = "materials"
    LABOR = "labor"
    FUEL = "fuel"
    EQUIPMENT = "equipment"
    VEHICLE = "vehicle"
    INSURANCE = "insurance"
    MARKETING = "marketing"
    OFFICE = "office"
    SUBCONTRACTOR = "subcontractor"
    OTHER = "other"


class CampaignType(str, Enum):
    """Marketing campaign type.

    Validates: CRM Gap Closure Req 45.1
    """

    EMAIL = "email"
    SMS = "sms"
    BOTH = "both"


class CampaignStatus(str, Enum):
    """Marketing campaign lifecycle status.

    Validates: CRM Gap Closure Req 45.1
    """

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    CANCELLED = "cancelled"


class MediaType(str, Enum):
    """Media library item type.

    Validates: CRM Gap Closure Req 49.1
    """

    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"


class BreakType(str, Enum):
    """Staff break type.

    Validates: CRM Gap Closure Req 42.3
    """

    LUNCH = "lunch"
    GAS = "gas"
    PERSONAL = "personal"
    OTHER = "other"


class NotificationType(str, Enum):
    """Notification type for customer communications.

    Validates: CRM Gap Closure Req 39.1, 54.1
    """

    DAY_OF_REMINDER = "day_of_reminder"
    ON_MY_WAY = "on_my_way"
    ARRIVAL = "arrival"
    DELAY = "delay"
    COMPLETION = "completion"
    INVOICE_PRE_DUE = "invoice_pre_due"
    INVOICE_PAST_DUE = "invoice_past_due"
    INVOICE_LIEN = "invoice_lien"
    REVIEW_REQUEST = "review_request"
    LEAD_CONFIRMATION = "lead_confirmation"
    ESTIMATE_SENT = "estimate_sent"
    CONTRACT_SENT = "contract_sent"
    CAMPAIGN = "campaign"


class FollowUpStatus(str, Enum):
    """Estimate follow-up status.

    Validates: CRM Gap Closure Req 51.1
    """

    SCHEDULED = "scheduled"
    SENT = "sent"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


class AlertSeverity(str, Enum):
    """Severity level for admin-facing alerts.

    Validates: bughunt 2026-04-16 H-5 (admin cancellation alert on C reply).
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class AlertType(str, Enum):
    """Type classification for admin-facing alerts.

    Validates: bughunt 2026-04-16 H-5 (admin cancellation alert on C reply).
    """

    CUSTOMER_CANCELLED_APPOINTMENT = "customer_cancelled_appointment"
    CONFIRMATION_NO_REPLY = "confirmation_no_reply"
    LATE_RESCHEDULE_ATTEMPT = "late_reschedule_attempt"
    CUSTOMER_RECONSIDER_CANCELLATION = "customer_reconsider_cancellation"


# =============================================================================
# CRM Changes Update 2 Enums
# =============================================================================


class SalesEntryStatus(str, Enum):
    """Sales pipeline entry status.

    Validates: CRM Changes Update 2 Req 14.3
    """

    SCHEDULE_ESTIMATE = "schedule_estimate"
    ESTIMATE_SCHEDULED = "estimate_scheduled"
    SEND_ESTIMATE = "send_estimate"
    PENDING_APPROVAL = "pending_approval"
    SEND_CONTRACT = "send_contract"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


# Ordered pipeline for auto-advance (non-terminal only)
SALES_PIPELINE_ORDER: list[SalesEntryStatus] = [
    SalesEntryStatus.SCHEDULE_ESTIMATE,
    SalesEntryStatus.ESTIMATE_SCHEDULED,
    SalesEntryStatus.SEND_ESTIMATE,
    SalesEntryStatus.PENDING_APPROVAL,
    SalesEntryStatus.SEND_CONTRACT,
    SalesEntryStatus.CLOSED_WON,
]

SALES_TERMINAL_STATUSES: set[SalesEntryStatus] = {
    SalesEntryStatus.CLOSED_WON,
    SalesEntryStatus.CLOSED_LOST,
}

VALID_SALES_TRANSITIONS: dict[SalesEntryStatus, set[SalesEntryStatus]] = {
    SalesEntryStatus.SCHEDULE_ESTIMATE: {
        SalesEntryStatus.ESTIMATE_SCHEDULED,
        SalesEntryStatus.CLOSED_LOST,
    },
    SalesEntryStatus.ESTIMATE_SCHEDULED: {
        SalesEntryStatus.SEND_ESTIMATE,
        SalesEntryStatus.CLOSED_LOST,
    },
    SalesEntryStatus.SEND_ESTIMATE: {
        SalesEntryStatus.PENDING_APPROVAL,
        SalesEntryStatus.CLOSED_LOST,
    },
    SalesEntryStatus.PENDING_APPROVAL: {
        SalesEntryStatus.SEND_CONTRACT,
        SalesEntryStatus.CLOSED_LOST,
    },
    SalesEntryStatus.SEND_CONTRACT: {
        SalesEntryStatus.CLOSED_WON,
        SalesEntryStatus.CLOSED_LOST,
    },
    SalesEntryStatus.CLOSED_WON: set(),
    SalesEntryStatus.CLOSED_LOST: set(),
}


class ConfirmationKeyword(str, Enum):
    """Y/R/C confirmation reply keywords.

    Validates: CRM Changes Update 2 Req 24.1
    """

    CONFIRM = "confirm"
    RESCHEDULE = "reschedule"
    CANCEL = "cancel"


class DocumentType(str, Enum):
    """Customer document type classification.

    Validates: CRM Changes Update 2 Req 17.3
    """

    ESTIMATE = "estimate"
    CONTRACT = "contract"
    PHOTO = "photo"
    DIAGRAM = "diagram"
    REFERENCE = "reference"
    SIGNED_CONTRACT = "signed_contract"


class ProposalStatus(str, Enum):
    """Contract renewal proposal status.

    Validates: CRM Changes Update 2 Req 31.1
    """

    PENDING = "pending"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    REJECTED = "rejected"


class ProposedJobStatus(str, Enum):
    """Contract renewal proposed job status.

    Validates: CRM Changes Update 2 Req 31.1
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class MessageType(str, Enum):
    """SMS message type classification.

    Validates: CRM Changes Update 2 Req 14.3, 24.1
    """

    APPOINTMENT_CONFIRMATION = "appointment_confirmation"
    APPOINTMENT_RESCHEDULE = "appointment_reschedule"
    APPOINTMENT_CANCELLATION = "appointment_cancellation"
    APPOINTMENT_REMINDER = "appointment_reminder"
    ON_THE_WAY = "on_the_way"
    ARRIVAL = "arrival"
    COMPLETION = "completion"
    INVOICE = "invoice"
    PAYMENT_REMINDER = "payment_reminder"
    CUSTOM = "custom"
    LEAD_CONFIRMATION = "lead_confirmation"
    ESTIMATE_SENT = "estimate_sent"
    CONTRACT_SENT = "contract_sent"
    REVIEW_REQUEST = "review_request"
    CAMPAIGN = "campaign"
    GOOGLE_REVIEW_REQUEST = "google_review_request"
    ON_MY_WAY = "on_my_way"
    AUTOMATED_NOTIFICATION = "automated_notification"
    # bughunt M-9: outbound replies to inbound Y/R/C and the reschedule
    # follow-up SMS now route through send_message and need their own
    # message_type so per-type dedup and audit reporting stay meaningful.
    APPOINTMENT_CONFIRMATION_REPLY = "appointment_confirmation_reply"
    RESCHEDULE_FOLLOWUP = "reschedule_followup"


class MergeCandidateStatus(str, Enum):
    """Customer merge candidate review status.

    Validates: CRM Changes Update 2 Req 5.6
    """

    PENDING = "pending"
    MERGED = "merged"
    DISMISSED = "dismissed"


# =============================================================================
# Job type display names (bughunt L-1, L-8)
# =============================================================================
#
# ``jobs.job_type`` is a free-text column — agreements, lead conversions,
# and manual jobs all seed it with slugs like ``spring_startup`` or
# ``fall_winterization``. Both the customer-facing confirmation SMS and the
# Sales-pipeline list render these slugs to humans, so we need a canonical
# display map. Uncurated slugs (rare/ad-hoc values) fall through to a
# title-cased replacement via ``job_type_display()`` so the output never
# reads like a database identifier.

JOB_TYPE_DISPLAY: dict[str, str] = {
    "spring_startup": "Spring Startup",
    "fall_winterization": "Fall Winterization",
    "fall_blowout": "Fall Blowout",
    "mid_season_inspection": "Mid-Season Inspection",
    "monthly_visit": "Monthly Visit",
    "winterization": "Winterization",
    "seasonal_maintenance": "Seasonal Maintenance",
    "small_repair": "Small Repair",
    "new_system": "New System Installation",
    "new_installation": "New System Installation",
    "upgrade": "System Upgrade",
    "system_upgrade": "System Upgrade",
    "repair": "Repair",
    "consultation": "Consultation",
    "installation": "Installation",
    "custom_installation": "Custom Installation",
    "diagnostic": "Diagnostic",
    "service_call": "Service Call",
    "estimate": "Estimate Visit",
    "hoa_irrigation_audit": "HOA Irrigation Audit",
}


def job_type_display(job_type: str | None) -> str:
    """Render a ``jobs.job_type`` slug as a customer-facing display name.

    Uses :data:`JOB_TYPE_DISPLAY` for known slugs; falls back to title-cased
    underscore-to-space replacement so ad-hoc values still read reasonably
    ("spring_startup" → "Spring Startup", "hoa_irrigation_audit" maps
    explicitly to "HOA Irrigation Audit" rather than "Hoa Irrigation Audit").
    Returns an empty string for ``None`` / empty input so callers can safely
    compose templates.
    """
    if not job_type:
        return ""
    mapped = JOB_TYPE_DISPLAY.get(job_type)
    if mapped is not None:
        return mapped
    return job_type.replace("_", " ").title()


# =============================================================================
# Valid Appointment Status Transitions
# =============================================================================

VALID_APPOINTMENT_STATUS_TRANSITIONS: dict[
    AppointmentStatus,
    set[AppointmentStatus],
] = {
    AppointmentStatus.PENDING: {
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.SCHEDULED: {
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.EN_ROUTE,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.CONFIRMED: {
        AppointmentStatus.EN_ROUTE,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.EN_ROUTE: {
        AppointmentStatus.IN_PROGRESS,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.IN_PROGRESS: {
        AppointmentStatus.COMPLETED,
        AppointmentStatus.CANCELLED,
    },
    AppointmentStatus.COMPLETED: set(),  # terminal
    AppointmentStatus.CANCELLED: set(),  # terminal
    AppointmentStatus.NO_SHOW: set(),  # terminal
}


VALID_AGREEMENT_STATUS_TRANSITIONS: dict[
    AgreementStatus,
    set[AgreementStatus],
] = {
    AgreementStatus.PENDING: {AgreementStatus.ACTIVE, AgreementStatus.CANCELLED},
    AgreementStatus.ACTIVE: {
        AgreementStatus.PAST_DUE,
        AgreementStatus.PENDING_RENEWAL,
        AgreementStatus.CANCELLED,
        AgreementStatus.EXPIRED,
        AgreementStatus.PAUSED,
    },
    AgreementStatus.PAST_DUE: {
        AgreementStatus.ACTIVE,
        AgreementStatus.PAUSED,
        AgreementStatus.CANCELLED,
    },
    AgreementStatus.PAUSED: {
        AgreementStatus.ACTIVE,
        AgreementStatus.CANCELLED,
    },
    AgreementStatus.PENDING_RENEWAL: {
        AgreementStatus.ACTIVE,
        AgreementStatus.EXPIRED,
        AgreementStatus.CANCELLED,
    },
    AgreementStatus.CANCELLED: set(),  # terminal
    AgreementStatus.EXPIRED: {AgreementStatus.ACTIVE},  # win-back re-subscription
}
