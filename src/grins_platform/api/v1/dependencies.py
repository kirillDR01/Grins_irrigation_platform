"""
FastAPI dependency injection for API v1.

This module provides dependency injection functions for services
and other shared resources used by API endpoints.

Validates: Requirement 10.5-10.7
"""

from __future__ import annotations

from collections.abc import (
    AsyncGenerator,
)
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import (
    AsyncSession,  # noqa: TC002 - Required at runtime for FastAPI
)

from grins_platform.database import get_db_session as db_session_generator
from grins_platform.repositories.appointment_repository import AppointmentRepository
from grins_platform.repositories.campaign_repository import CampaignRepository
from grins_platform.repositories.customer_repository import CustomerRepository
from grins_platform.repositories.estimate_repository import EstimateRepository
from grins_platform.repositories.google_sheet_submission_repository import (
    GoogleSheetSubmissionRepository,
)
from grins_platform.repositories.job_repository import JobRepository
from grins_platform.repositories.lead_repository import LeadRepository
from grins_platform.repositories.property_repository import PropertyRepository
from grins_platform.repositories.service_offering_repository import (
    ServiceOfferingRepository,
)
from grins_platform.repositories.staff_repository import StaffRepository
from grins_platform.services.appointment_service import AppointmentService
from grins_platform.services.appointment_timeline_service import (
    AppointmentTimelineService,
)
from grins_platform.services.campaign_service import CampaignService
from grins_platform.services.customer_merge_service import CustomerMergeService
from grins_platform.services.customer_service import CustomerService
from grins_platform.services.dashboard_service import DashboardService
from grins_platform.services.duplicate_detection_service import (
    DuplicateDetectionService,
)
from grins_platform.services.email_service import EmailService
from grins_platform.services.estimate_service import EstimateService
from grins_platform.services.google_sheets_service import GoogleSheetsService
from grins_platform.services.job_service import JobService
from grins_platform.services.photo_service import PhotoService
from grins_platform.services.property_service import PropertyService
from grins_platform.services.service_offering_service import ServiceOfferingService
from grins_platform.services.sms.factory import get_sms_provider
from grins_platform.services.sms_service import SMSService
from grins_platform.services.staff_availability_service import StaffAvailabilityService
from grins_platform.services.staff_service import StaffService


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency.

    Yields:
        AsyncSession for database operations
    """
    async for session in db_session_generator():
        yield session


async def get_customer_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CustomerService:
    """Get CustomerService dependency.

    Both CustomerRepository and PropertyRepository are constructed against
    the same AsyncSession so that creating a customer together with a
    primary property stays atomic.

    Args:
        session: Database session from dependency injection

    Returns:
        CustomerService instance
    """
    repository = CustomerRepository(session=session)
    property_repository = PropertyRepository(session=session)
    return CustomerService(
        repository=repository,
        property_repository=property_repository,
    )


def get_duplicate_detection_service() -> DuplicateDetectionService:
    """Get DuplicateDetectionService dependency."""
    return DuplicateDetectionService()


def get_customer_merge_service() -> CustomerMergeService:
    """Get CustomerMergeService dependency."""
    return CustomerMergeService()


async def get_property_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PropertyService:
    """Get PropertyService dependency.

    This creates a PropertyService with a PropertyRepository using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        PropertyService instance
    """
    repository = PropertyRepository(session=session)
    return PropertyService(repository=repository)


async def get_service_offering_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ServiceOfferingService:
    """Get ServiceOfferingService dependency.

    This creates a ServiceOfferingService with a ServiceOfferingRepository using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        ServiceOfferingService instance
    """
    repository = ServiceOfferingRepository(session=session)
    return ServiceOfferingService(repository=repository)


async def get_staff_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StaffService:
    """Get StaffService dependency.

    This creates a StaffService with a StaffRepository using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        StaffService instance
    """
    repository = StaffRepository(session=session)
    return StaffService(repository=repository)


async def get_job_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> JobService:
    """Get JobService dependency.

    This creates a JobService with all required repositories using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        JobService instance
    """
    job_repository = JobRepository(session=session)
    customer_repository = CustomerRepository(session=session)
    property_repository = PropertyRepository(session=session)
    service_repository = ServiceOfferingRepository(session=session)
    return JobService(
        job_repository=job_repository,
        customer_repository=customer_repository,
        property_repository=property_repository,
        service_repository=service_repository,
    )


async def get_appointment_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AppointmentService:
    """Get AppointmentService dependency.

    This creates an AppointmentService with all required repositories using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        AppointmentService instance
    """
    appointment_repository = AppointmentRepository(session=session)
    job_repository = JobRepository(session=session)
    staff_repository = StaffRepository(session=session)
    return AppointmentService(
        appointment_repository=appointment_repository,
        job_repository=job_repository,
        staff_repository=staff_repository,
    )


async def get_appointment_timeline_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AppointmentTimelineService:
    """Provide an AppointmentTimelineService for Gap 11."""
    return AppointmentTimelineService(session=session)


async def get_full_appointment_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AppointmentService:
    """Get AppointmentService with invoice and estimate support.

    Includes InvoiceRepository and EstimateService for payment collection,
    invoice creation, and estimate creation from appointments.

    Args:
        session: Database session from dependency injection

    Returns:
        AppointmentService instance with full capabilities
    """
    from grins_platform.repositories.invoice_repository import (  # noqa: PLC0415
        InvoiceRepository,
    )

    appointment_repository = AppointmentRepository(session=session)
    job_repository = JobRepository(session=session)
    staff_repository = StaffRepository(session=session)
    invoice_repository = InvoiceRepository(session=session)
    estimate_repository = EstimateRepository(session=session)
    estimate_service = EstimateService(estimate_repository=estimate_repository)
    return AppointmentService(
        appointment_repository=appointment_repository,
        job_repository=job_repository,
        staff_repository=staff_repository,
        invoice_repository=invoice_repository,
        estimate_service=estimate_service,
    )


async def get_dashboard_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DashboardService:
    """Get DashboardService dependency.

    This creates a DashboardService with all required repositories using
    the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        DashboardService instance
    """
    from grins_platform.repositories.invoice_repository import (  # noqa: PLC0415
        InvoiceRepository,
    )

    customer_repository = CustomerRepository(session=session)
    job_repository = JobRepository(session=session)
    staff_repository = StaffRepository(session=session)
    appointment_repository = AppointmentRepository(session=session)
    lead_repository = LeadRepository(session=session)
    invoice_repository = InvoiceRepository(session=session)
    return DashboardService(
        customer_repository=customer_repository,
        job_repository=job_repository,
        staff_repository=staff_repository,
        appointment_repository=appointment_repository,
        lead_repository=lead_repository,
        invoice_repository=invoice_repository,
        session=session,
    )


async def get_staff_availability_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StaffAvailabilityService:
    """Get StaffAvailabilityService dependency.

    This creates a StaffAvailabilityService using the injected database session.

    Args:
        session: Database session from dependency injection

    Returns:
        StaffAvailabilityService instance
    """
    return StaffAvailabilityService(session=session)


async def get_google_sheet_submission_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> GoogleSheetSubmissionRepository:
    """Get GoogleSheetSubmissionRepository dependency.

    Args:
        session: Database session from dependency injection

    Returns:
        GoogleSheetSubmissionRepository instance
    """
    return GoogleSheetSubmissionRepository(session=session)


async def get_sheets_service() -> GoogleSheetsService:
    """Get GoogleSheetsService for API use.

    The service is stateless — repos are created per-call inside
    each service method using the session parameter.

    Returns:
        GoogleSheetsService instance
    """
    return GoogleSheetsService(submission_repo=None, lead_repo=None)


def get_photo_service() -> PhotoService:
    """Get PhotoService dependency.

    Returns:
        PhotoService instance with default S3 client
    """
    return PhotoService()


async def get_estimate_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> EstimateService:
    """Get EstimateService dependency.

    Args:
        session: Database session from dependency injection

    Returns:
        EstimateService instance
    """
    repository = EstimateRepository(session=session)
    return EstimateService(estimate_repository=repository)


async def get_campaign_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CampaignService:
    """Get CampaignService with SMS and Email dependencies wired.

    Fixes B1: CampaignService now receives SMSService and EmailService
    so campaign sends actually dispatch messages.

    Args:
        session: Database session from dependency injection.

    Returns:
        CampaignService with all dependencies.
    """
    repo = CampaignRepository(session)
    provider = get_sms_provider()
    sms_service = SMSService(session=session, provider=provider)
    email_service = EmailService()
    return CampaignService(
        campaign_repository=repo,
        sms_service=sms_service,
        email_service=email_service,
    )


__all__ = [
    "get_appointment_service",
    "get_campaign_service",
    "get_customer_service",
    "get_dashboard_service",
    "get_db_session",
    "get_estimate_service",
    "get_full_appointment_service",
    "get_google_sheet_submission_repository",
    "get_job_service",
    "get_photo_service",
    "get_property_service",
    "get_service_offering_service",
    "get_sheets_service",
    "get_staff_availability_service",
    "get_staff_service",
]
