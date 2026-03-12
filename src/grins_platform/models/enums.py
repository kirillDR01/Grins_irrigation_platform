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

    Validates: Requirement 4.1
    """

    REQUESTED = "requested"
    APPROVED = "approved"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    CLOSED = "closed"


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

    Validates: Admin Dashboard Requirement 1.3
    """

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


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
    """

    CASH = "cash"
    CHECK = "check"
    VENMO = "venmo"
    ZELLE = "zelle"
    STRIPE = "stripe"


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
