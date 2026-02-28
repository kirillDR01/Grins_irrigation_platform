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
"""

from grins_platform.models.ai_audit_log import AIAuditLog
from grins_platform.models.ai_usage import AIUsage
from grins_platform.models.appointment import Appointment
from grins_platform.models.customer import Customer
from grins_platform.models.enums import (
    AppointmentStatus,
    CustomerStatus,
    InvoiceStatus,
    JobCategory,
    JobSource,
    JobStatus,
    LeadSituation,
    LeadSource,
    LeadStatus,
    PaymentMethod,
    PricingModel,
    PropertyType,
    ServiceCategory,
    SkillLevel,
    StaffRole,
    SystemType,
)
from grins_platform.models.invoice import Invoice
from grins_platform.models.job import Job
from grins_platform.models.job_status_history import JobStatusHistory
from grins_platform.models.lead import Lead
from grins_platform.models.property import Property
from grins_platform.models.schedule_clear_audit import ScheduleClearAudit
from grins_platform.models.sent_message import SentMessage
from grins_platform.models.service_offering import ServiceOffering
from grins_platform.models.staff import Staff
from grins_platform.models.staff_availability import StaffAvailability

__all__ = [
    # Phase 6: AI Assistant
    "AIAuditLog",
    "AIUsage",
    # Phase 3: Admin Dashboard
    "Appointment",
    "AppointmentStatus",
    # Phase 1: Customer Management
    "Customer",
    "CustomerStatus",
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
    "LeadStatus",
    "PaymentMethod",
    "PricingModel",
    "Property",
    "PropertyType",
    # Phase 8: Schedule Workflow
    "ScheduleClearAudit",
    # Phase 6: AI Assistant
    "SentMessage",
    "ServiceCategory",
    "ServiceOffering",
    "SkillLevel",
    "Staff",
    # Phase 4: Route Optimization
    "StaffAvailability",
    "StaffRole",
    "SystemType",
]
