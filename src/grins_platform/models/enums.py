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
