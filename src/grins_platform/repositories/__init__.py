"""
Repository layer for database operations.

This module provides repository classes for data access operations,
following the repository pattern for clean separation of concerns.
"""

from grins_platform.repositories.agreement_repository import AgreementRepository
from grins_platform.repositories.agreement_tier_repository import (
    AgreementTierRepository,
)
from grins_platform.repositories.ai_audit_log_repository import AIAuditLogRepository
from grins_platform.repositories.ai_usage_repository import AIUsageRepository
from grins_platform.repositories.appointment_repository import AppointmentRepository
from grins_platform.repositories.audit_log_repository import AuditLogRepository
from grins_platform.repositories.campaign_repository import CampaignRepository
from grins_platform.repositories.campaign_response_repository import (
    CampaignResponseRepository,
)
from grins_platform.repositories.communication_repository import (
    CommunicationRepository,
)
from grins_platform.repositories.consent_language_version_repository import (
    ConsentLanguageVersionRepository,
)
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.estimate_repository import EstimateRepository
from grins_platform.repositories.expense_repository import ExpenseRepository
from grins_platform.repositories.invoice_repository import InvoiceRepository
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.marketing_budget_repository import (
    MarketingBudgetRepository,
)
from grins_platform.repositories.media_repository import MediaRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.repositories.schedule_clear_audit_repository import (
    ScheduleClearAuditRepository,
)
from grins_platform.repositories.sent_message_repository import SentMessageRepository
from grins_platform.repositories.service_offering_repository import (
    ServiceOfferingRepository,
)
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.repositories.stripe_webhook_event_repository import (
    StripeWebhookEventRepository,
)

__all__ = [
    "AIAuditLogRepository",
    "AIUsageRepository",
    "AgreementRepository",
    "AgreementTierRepository",
    "AppointmentRepository",
    "AuditLogRepository",
    "CampaignRepository",
    "CampaignResponseRepository",
    "CommunicationRepository",
    "ConsentLanguageVersionRepository",
    "CustomerRepository",
    "EstimateRepository",
    "ExpenseRepository",
    "InvoiceRepository",
    "JobRepository",
    "MarketingBudgetRepository",
    "MediaRepository",
    "PropertyRepository",
    "ScheduleClearAuditRepository",
    "SentMessageRepository",
    "ServiceOfferingRepository",
    "StaffRepository",
    "StripeWebhookEventRepository",
]
