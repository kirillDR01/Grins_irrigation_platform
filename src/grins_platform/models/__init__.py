"""
SQLAlchemy models for Grin's Irrigation Platform.

This package contains all database models used by the platform.

Phase 1 (Customer Management): Customer, Property
Phase 2 (Field Operations): ServiceOffering, Job, JobStatusHistory, Staff
Phase 3 (Admin Dashboard): Appointment
Phase 4 (Route Optimization): StaffAvailability
Phase 6 (AI Assistant): AIAuditLog, AIUsage, SentMessage
Phase 8 (Schedule Workflow): ScheduleClearAudit, Invoice
Phase 9 (Lead Capture): Lead
Phase 10 (Google Sheets): GoogleSheetSubmission
"""

from grins_platform.models.agreement_status_log import AgreementStatusLog
from grins_platform.models.ai_audit_log import AIAuditLog
from grins_platform.models.ai_usage import AIUsage
from grins_platform.models.appointment import Appointment
from grins_platform.models.consent_language_version import ConsentLanguageVersion
from grins_platform.models.customer import Customer
from grins_platform.models.disclosure_record import DisclosureRecord
from grins_platform.models.email_suppression_list import EmailSuppressionList
from grins_platform.models.enums import (
    AgreementPaymentStatus,
    AgreementStatus,
    AppointmentStatus,
    BillingFrequency,
    CustomerStatus,
    DisclosureType,
    EmailType,
    IntakeTag,
    InvoiceStatus,
    JobCategory,
    JobSource,
    JobStatus,
    LeadSituation,
    LeadSource,
    LeadSourceExtended,
    LeadStatus,
    PackageType,
    PaymentMethod,
    PricingModel,
    PropertyType,
    ServiceCategory,
    SkillLevel,
    StaffRole,
    SystemType,
    WebhookProcessingStatus,
)
from grins_platform.models.google_sheet_submission import GoogleSheetSubmission
from grins_platform.models.invoice import Invoice
from grins_platform.models.job import Job
from grins_platform.models.job_status_history import JobStatusHistory
from grins_platform.models.lead import Lead
from grins_platform.models.property import Property
from grins_platform.models.schedule_clear_audit import ScheduleClearAudit
from grins_platform.models.sent_message import SentMessage
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.models.service_agreement_tier import ServiceAgreementTier
from grins_platform.models.service_offering import ServiceOffering
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.models.staff import Staff
from grins_platform.models.staff_availability import StaffAvailability
from grins_platform.models.stripe_webhook_event import StripeWebhookEvent

__all__ = [
    # Phase 6: AI Assistant
    "AIAuditLog",
    "AIUsage",
    # Service Package Purchases
    "AgreementPaymentStatus",
    "AgreementStatus",
    "AgreementStatusLog",
    # Phase 3: Admin Dashboard
    "Appointment",
    "AppointmentStatus",
    "BillingFrequency",
    "ConsentLanguageVersion",
    # Phase 1: Customer Management
    "Customer",
    "CustomerStatus",
    "DisclosureRecord",
    "DisclosureType",
    "EmailSuppressionList",
    "EmailType",
    # Phase 10: Google Sheets
    "GoogleSheetSubmission",
    "IntakeTag",
    # Phase 8: Invoice Management
    "Invoice",
    "InvoiceStatus",
    # Phase 2: Field Operations
    "Job",
    "JobCategory",
    "JobSource",
    "JobStatus",
    "JobStatusHistory",
    # Phase 9: Lead Capture
    "Lead",
    "LeadSituation",
    "LeadSource",
    "LeadSourceExtended",
    "LeadStatus",
    "PackageType",
    "PaymentMethod",
    "PricingModel",
    "Property",
    "PropertyType",
    # Phase 8: Schedule Workflow
    "ScheduleClearAudit",
    # Phase 6: AI Assistant
    "SentMessage",
    # Service Package Purchases
    "ServiceAgreement",
    "ServiceAgreementTier",
    "ServiceCategory",
    "ServiceOffering",
    "SkillLevel",
    "SmsConsentRecord",
    "Staff",
    # Phase 4: Route Optimization
    "StaffAvailability",
    "StaffRole",
    "StripeWebhookEvent",
    "SystemType",
    "WebhookProcessingStatus",
]
