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
CRM Gap Closure: Communication, CustomerPhoto, LeadAttachment, EstimateTemplate,
    ContractTemplate, Estimate, EstimateFollowUp, Expense, Campaign,
    CampaignRecipient, MarketingBudget, MediaLibraryItem, StaffBreak,
    AuditLog, BusinessSetting
AI Scheduling: SchedulingCriteriaConfig, SchedulingAlert, ChangeRequest,
    SchedulingChatSession, ResourceTruckInventory, ServiceZone
"""

from grins_platform.models.admin_notification import AdminNotification
from grins_platform.models.agreement_status_log import AgreementStatusLog
from grins_platform.models.ai_audit_log import AIAuditLog
from grins_platform.models.ai_usage import AIUsage
from grins_platform.models.alert import Alert
from grins_platform.models.appointment import Appointment
from grins_platform.models.appointment_attachment import AppointmentAttachment
from grins_platform.models.appointment_note import AppointmentNote
from grins_platform.models.appointment_reminder_log import AppointmentReminderLog
from grins_platform.models.audit_log import AuditLog
from grins_platform.models.business_setting import BusinessSetting
from grins_platform.models.campaign import Campaign, CampaignRecipient
from grins_platform.models.campaign_response import CampaignResponse
from grins_platform.models.change_request import ChangeRequest
from grins_platform.models.communication import Communication
from grins_platform.models.consent_language_version import ConsentLanguageVersion
from grins_platform.models.contract_renewal import (
    ContractRenewalProposal,
    ContractRenewalProposedJob,
)
from grins_platform.models.contract_template import ContractTemplate
from grins_platform.models.customer import Customer
from grins_platform.models.customer_document import CustomerDocument
from grins_platform.models.customer_merge_candidate import CustomerMergeCandidate
from grins_platform.models.customer_photo import CustomerPhoto
from grins_platform.models.customer_tag import CustomerTag
from grins_platform.models.disclosure_record import DisclosureRecord
from grins_platform.models.email_suppression_list import EmailSuppressionList
from grins_platform.models.enums import (
    ActionTag,
    AdminNotificationEventType,
    AgreementPaymentStatus,
    AgreementStatus,
    AlertSeverity,
    AlertType,
    AppointmentStatus,
    AttachmentType,
    BillingFrequency,
    BreakType,
    CampaignStatus,
    CampaignType,
    CommunicationChannel,
    CommunicationDirection,
    ConfirmationKeyword,
    CustomerStatus,
    DisclosureType,
    DocumentType,
    EmailType,
    EstimateStatus,
    ExpenseCategory,
    FollowUpStatus,
    IntakeTag,
    InvoiceStatus,
    JobCategory,
    JobSource,
    JobStatus,
    LeadSituation,
    LeadSource,
    LeadSourceExtended,
    LeadStatus,
    MediaType,
    MergeCandidateStatus,
    MessageType,
    NotificationType,
    PackageType,
    PaymentMethod,
    PricingModel,
    PropertyType,
    ProposalStatus,
    ProposedJobStatus,
    SalesEntryStatus,
    ServiceCategory,
    SkillLevel,
    StaffRole,
    SystemType,
    WebhookProcessingStatus,
)
from grins_platform.models.estimate import Estimate
from grins_platform.models.estimate_follow_up import EstimateFollowUp
from grins_platform.models.estimate_template import EstimateTemplate
from grins_platform.models.expense import Expense
from grins_platform.models.google_sheet_submission import GoogleSheetSubmission
from grins_platform.models.invoice import Invoice
from grins_platform.models.job import Job
from grins_platform.models.job_confirmation import (
    JobConfirmationResponse,
    RescheduleRequest,
)
from grins_platform.models.job_status_history import JobStatusHistory
from grins_platform.models.lead import Lead
from grins_platform.models.lead_attachment import LeadAttachment
from grins_platform.models.marketing_budget import MarketingBudget
from grins_platform.models.media_library import MediaLibraryItem
from grins_platform.models.property import Property
from grins_platform.models.resource_truck_inventory import ResourceTruckInventory
from grins_platform.models.sales import SalesCalendarEvent, SalesEntry
from grins_platform.models.schedule_clear_audit import ScheduleClearAudit
from grins_platform.models.scheduling_alert import SchedulingAlert
from grins_platform.models.scheduling_chat_session import SchedulingChatSession
from grins_platform.models.scheduling_criteria_config import SchedulingCriteriaConfig
from grins_platform.models.sent_message import SentMessage
from grins_platform.models.service_agreement import ServiceAgreement
from grins_platform.models.service_agreement_tier import ServiceAgreementTier
from grins_platform.models.service_offering import ServiceOffering
from grins_platform.models.service_zone import ServiceZone
from grins_platform.models.sms_consent_record import SmsConsentRecord
from grins_platform.models.staff import Staff
from grins_platform.models.staff_availability import StaffAvailability
from grins_platform.models.staff_break import StaffBreak
from grins_platform.models.stripe_webhook_event import StripeWebhookEvent
from grins_platform.models.webauthn_credential import (
    WebAuthnCredential,
    WebAuthnUserHandle,
)
from grins_platform.models.webhook_processed_log import WebhookProcessedLog

__all__ = [
    # Phase 6: AI Assistant
    "AIAuditLog",
    "AIUsage",
    # CRM Gap Closure
    "ActionTag",
    # Cluster H §5: Admin in-app notifications inbox
    "AdminNotification",
    "AdminNotificationEventType",
    # Service Package Purchases
    "AgreementPaymentStatus",
    "AgreementStatus",
    "AgreementStatusLog",
    # bughunt 2026-04-16 H-5: admin alerts
    "Alert",
    "AlertSeverity",
    "AlertType",
    # Phase 3: Admin Dashboard
    "Appointment",
    # April 16th: Appointment Attachments
    "AppointmentAttachment",
    # Appointment Modal V2: Internal Notes
    "AppointmentNote",
    # scheduling gaps gap-10 Phase 1: Day-2 No-Reply Reminder
    "AppointmentReminderLog",
    "AppointmentStatus",
    "AttachmentType",
    # CRM Gap Closure
    "AuditLog",
    "BillingFrequency",
    "BreakType",
    "BusinessSetting",
    "Campaign",
    "CampaignRecipient",
    "CampaignResponse",
    "CampaignStatus",
    "CampaignType",
    # AI Scheduling: Change Requests
    "ChangeRequest",
    "Communication",
    "CommunicationChannel",
    "CommunicationDirection",
    # CRM Changes Update 2
    "ConfirmationKeyword",
    "ConsentLanguageVersion",
    "ContractRenewalProposal",
    "ContractRenewalProposedJob",
    "ContractTemplate",
    # Phase 1: Customer Management
    "Customer",
    "CustomerDocument",
    "CustomerMergeCandidate",
    "CustomerPhoto",
    "CustomerStatus",
    "CustomerTag",
    "DisclosureRecord",
    "DisclosureType",
    "DocumentType",
    "EmailSuppressionList",
    "EmailType",
    "Estimate",
    "EstimateFollowUp",
    "EstimateStatus",
    "EstimateTemplate",
    "Expense",
    "ExpenseCategory",
    "FollowUpStatus",
    # Phase 10: Google Sheets
    "GoogleSheetSubmission",
    "IntakeTag",
    # Phase 8: Invoice Management
    "Invoice",
    "InvoiceStatus",
    # Phase 2: Field Operations
    "Job",
    "JobCategory",
    "JobConfirmationResponse",
    "JobSource",
    "JobStatus",
    "JobStatusHistory",
    # Phase 9: Lead Capture
    "Lead",
    "LeadAttachment",
    "LeadSituation",
    "LeadSource",
    "LeadSourceExtended",
    "LeadStatus",
    "MarketingBudget",
    "MediaLibraryItem",
    "MediaType",
    "MergeCandidateStatus",
    "MessageType",
    "NotificationType",
    "PackageType",
    "PaymentMethod",
    "PricingModel",
    "Property",
    "PropertyType",
    "ProposalStatus",
    "ProposedJobStatus",
    "RescheduleRequest",
    # AI Scheduling: Truck Inventory
    "ResourceTruckInventory",
    # Sales Pipeline
    "SalesCalendarEvent",
    "SalesEntry",
    "SalesEntryStatus",
    # Phase 8: Schedule Workflow
    "ScheduleClearAudit",
    # AI Scheduling: Alerts, Chat, Criteria Config
    "SchedulingAlert",
    "SchedulingChatSession",
    "SchedulingCriteriaConfig",
    # Phase 6: AI Assistant
    "SentMessage",
    # Service Package Purchases
    "ServiceAgreement",
    "ServiceAgreementTier",
    "ServiceCategory",
    "ServiceOffering",
    # AI Scheduling: Service Zones
    "ServiceZone",
    "SkillLevel",
    "SmsConsentRecord",
    "Staff",
    # Phase 4: Route Optimization
    "StaffAvailability",
    "StaffBreak",
    "StaffRole",
    "StripeWebhookEvent",
    "SystemType",
    "WebAuthnCredential",
    "WebAuthnUserHandle",
    "WebhookProcessedLog",
    "WebhookProcessingStatus",
]
