"""
SQLAlchemy models for Grin's Irrigation Platform.

This package contains all database models used by the platform.

Phase 1 (Customer Management): Customer, Property
Phase 2 (Field Operations): ServiceOffering, Job, JobStatusHistory, Staff
Phase 3 (Admin Dashboard): Appointment
"""

from grins_platform.models.appointment import Appointment
from grins_platform.models.customer import Customer
from grins_platform.models.enums import (
    AppointmentStatus,
    CustomerStatus,
    JobCategory,
    JobSource,
    JobStatus,
    LeadSource,
    PricingModel,
    PropertyType,
    ServiceCategory,
    SkillLevel,
    StaffRole,
    SystemType,
)
from grins_platform.models.job import Job
from grins_platform.models.job_status_history import JobStatusHistory
from grins_platform.models.property import Property
from grins_platform.models.service_offering import ServiceOffering
from grins_platform.models.staff import Staff

__all__ = [
    # Phase 3: Admin Dashboard
    "Appointment",
    "AppointmentStatus",
    # Phase 1: Customer Management
    "Customer",
    "CustomerStatus",
    # Phase 2: Field Operations
    "Job",
    "JobCategory",
    "JobSource",
    "JobStatus",
    "JobStatusHistory",
    "LeadSource",
    "PricingModel",
    "Property",
    "PropertyType",
    "ServiceCategory",
    "ServiceOffering",
    "SkillLevel",
    "Staff",
    "StaffRole",
    "SystemType",
]
