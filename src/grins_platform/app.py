"""
FastAPI application factory and configuration.

This module creates and configures the FastAPI application instance
with all routers, middleware, and exception handlers.

Validates: Requirement 10.5-10.7
"""

import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from grins_platform.api.v1.router import api_router
from grins_platform.database import get_database_manager
from grins_platform.exceptions import (
    ConfirmationCorrelationError,
    CustomerNotFoundError,
    DocumentUploadError,
    DuplicateCustomerError,
    DuplicateLeadError,
    InvalidLeadStatusTransitionError,
    InvalidSalesTransitionError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    LeadAlreadyConvertedError,
    LeadNotFoundError,
    MergeBlockerError,
    PropertyCustomerMismatchError,
    PropertyNotFoundError,
    RenewalProposalNotFoundError,
    ServiceOfferingInactiveError,
    ServiceOfferingNotFoundError,
    StaffNotFoundError,
    ValidationError,
    WebAuthnChallengeNotFoundError,
    WebAuthnCredentialNotFoundError,
    WebAuthnDuplicateCredentialError,
    WebAuthnVerificationError,
)
from grins_platform.log_config import (
    clear_request_id,
    get_logger,
    set_request_id,
)
from grins_platform.middleware.rate_limit import setup_rate_limiting
from grins_platform.middleware.request_size import (
    RequestSizeLimitMiddleware,
)
from grins_platform.middleware.security_headers import (
    SecurityHeadersMiddleware,
)
from grins_platform.scheduler import get_scheduler
from grins_platform.services.auth_service import validate_jwt_config
from grins_platform.services.background_jobs import register_scheduled_jobs
from grins_platform.services.google_sheets_config import GoogleSheetsSettings
from grins_platform.services.google_sheets_poller import GoogleSheetsPoller
from grins_platform.services.google_sheets_service import GoogleSheetsService
from grins_platform.services.signwell.client import (
    SignWellDocumentNotFoundError,
    SignWellError,
    SignWellWebhookVerificationError,
)
from grins_platform.services.sms.audit import log_provider_switched
from grins_platform.services.sms.factory import get_sms_provider
from grins_platform.services.stripe_config import StripeSettings

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager for startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    logger.info("app.startup_started", version="1.0.0")

    # Validate JWT configuration
    validate_jwt_config()

    db_manager = get_database_manager()
    health = await db_manager.health_check()
    logger.info("app.startup_database_check", **health)

    # Stripe configuration check
    stripe_settings = StripeSettings()
    stripe_settings.log_configuration_status()

    # Google Sheets poller
    poller: GoogleSheetsPoller | None = None
    try:
        settings = GoogleSheetsSettings()
        if settings.is_configured:
            service = GoogleSheetsService(submission_repo=None, lead_repo=None)
            poller = GoogleSheetsPoller(
                service=service,
                db_manager=db_manager,
                spreadsheet_id=settings.google_sheets_spreadsheet_id,
                sheet_name=settings.google_sheets_sheet_name,
                poll_interval=settings.google_sheets_poll_interval_seconds,
                key_path=settings.google_service_account_key_path,
                key_json=settings.google_service_account_key_json,
            )
            await poller.start()
            logger.info("app.sheets_poller_started")
        else:
            logger.info("app.sheets_poller_skipped", reason="not configured")
    except Exception as e:
        logger.warning("app.sheets_poller_startup_failed", error=str(e))
        poller = None

    app.state.sheets_poller = poller

    # Background scheduler
    bg_scheduler = get_scheduler()
    try:
        register_scheduled_jobs(bg_scheduler)
        bg_scheduler.start()
        logger.info("app.scheduler_started")
    except Exception as e:
        logger.warning("app.scheduler_startup_failed", error=str(e))

    # Log SMS provider selection at boot (Requirement 41)
    try:
        provider = get_sms_provider()
        provider_name = provider.provider_name
        logger.info("app.sms_provider_resolved", provider=provider_name)
        async for session in db_manager.get_session():
            await log_provider_switched(session, provider_name=provider_name)
    except Exception as e:
        logger.warning("app.sms_provider_audit_failed", error=str(e))

    logger.info("app.startup_completed")

    yield

    # Shutdown
    logger.info("app.shutdown_started")
    try:
        bg_scheduler.shutdown(wait=False)
        logger.info("app.scheduler_stopped")
    except Exception as e:
        logger.warning("app.scheduler_shutdown_failed", error=str(e))
    if app.state.sheets_poller is not None:
        await app.state.sheets_poller.stop()
        logger.info("app.sheets_poller_stopped")
    await db_manager.close()
    logger.info("app.shutdown_completed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="Grin's Irrigation Platform API",
        description="Field service automation API for irrigation business management",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # Configure CORS - read from environment variable or use defaults for local dev
    # CORS_ORIGINS should be a comma-separated list of allowed origins
    # Example: "https://grins-irrigation-platform.vercel.app,https://example.com"
    cors_origins_env = os.getenv("CORS_ORIGINS", "")

    # Default origins for local development
    default_origins = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ]

    # Parse CORS_ORIGINS from environment (comma-separated)
    if cors_origins_env:
        env_origins = [
            origin.strip() for origin in cors_origins_env.split(",") if origin.strip()
        ]
        # Combine environment origins with defaults
        allowed_origins = env_origins + default_origins
    else:
        allowed_origins = default_origins

    logger.info("app.cors_configured", origins=allowed_origins)

    # Separate exact origins from regex patterns (entries containing *)
    exact_origins = [o for o in allowed_origins if "*" not in o]
    regex_patterns = [o for o in allowed_origins if "*" in o]

    # Build a combined regex from wildcard patterns (e.g. "https://app-*-team.vercel.app")
    origin_regex: str | None = None
    if regex_patterns:
        # Convert glob-style * to regex .* and escape the rest
        regex_parts = []
        for pattern in regex_patterns:
            escaped = re.escape(pattern).replace(r"\*", ".*")
            regex_parts.append(escaped)
        origin_regex = "^(" + "|".join(regex_parts) + ")$"

    # Catch-all unhandled-exception middleware. Added FIRST so it ends up
    # *inside* CORSMiddleware in the wrap order (Starlette wraps later-added
    # middleware as outermost). When this middleware catches an exception
    # and returns a JSONResponse, that response then goes back through
    # CORSMiddleware, which attaches Access-Control-Allow-Origin.
    # Without this, 5xx responses from `ServerErrorMiddleware` bypass CORS
    # and the browser sees an opaque "Network Error" instead of the real
    # status + body. (bughunt 2026-04-28 §Bug 4.)
    @app.middleware("http")  # type: ignore[untyped-decorator]
    async def _catch_unhandled_exceptions(
        request: Request,
        call_next: Any,  # noqa: ANN401
    ) -> Any:  # noqa: ANN401
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception(
                "api.exception.unhandled",
                path=request.url.path,
                method=request.method,
                error=str(exc),
                exc_type=type(exc).__name__,
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Internal server error",
                    },
                },
            )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=exact_origins,
        allow_origin_regex=origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Security middleware (applied in reverse order of addition)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    setup_rate_limiting(app)

    # X-Request-ID: attach/echo a per-request UUID on every response so
    # external callers (e.g. the marketing-site lead form) can capture it
    # and share with us to grep server logs. The ID is also bound to the
    # structured log context so every log line during the request emits
    # it. (E-BUG-B — observability hook.)
    @app.middleware("http")  # type: ignore[untyped-decorator]
    async def _attach_request_id(request: Request, call_next: Any) -> Any:
        incoming = request.headers.get("x-request-id")
        request_id = set_request_id(incoming)
        try:
            response = await call_next(request)
        finally:
            clear_request_id()
        response.headers["X-Request-ID"] = request_id
        return response

    # Register exception handlers
    _register_exception_handlers(app)

    # Include routers
    app.include_router(api_router)

    # Health check endpoint
    @app.get("/health", tags=["health"])  # type: ignore[untyped-decorator]
    async def health_check() -> dict[str, Any]:
        """Health check endpoint.

        Returns:
            Health status information
        """
        db_manager = get_database_manager()
        db_health = await db_manager.health_check()
        return {
            "status": "healthy" if db_health["status"] == "healthy" else "degraded",
            "version": "1.0.0",
            "database": db_health,
        }

    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(CustomerNotFoundError)  # type: ignore[untyped-decorator]
    async def customer_not_found_handler(
        request: Request,
        exc: CustomerNotFoundError,
    ) -> JSONResponse:
        """Handle CustomerNotFoundError exceptions."""
        logger.warning(
            "api.exception.customer_not_found",
            customer_id=str(exc.customer_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "CUSTOMER_NOT_FOUND",
                    "message": str(exc),
                    "customer_id": str(exc.customer_id),
                },
            },
        )

    @app.exception_handler(DuplicateCustomerError)  # type: ignore[untyped-decorator]
    async def duplicate_customer_handler(
        request: Request,
        exc: DuplicateCustomerError,
    ) -> JSONResponse:
        """Handle DuplicateCustomerError exceptions."""
        logger.warning(
            "api.exception.duplicate_customer",
            existing_id=str(exc.existing_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "DUPLICATE_CUSTOMER",
                    "message": "Customer with this phone number already exists",
                    "existing_id": str(exc.existing_id),
                },
            },
        )

    @app.exception_handler(PropertyNotFoundError)  # type: ignore[untyped-decorator]
    async def property_not_found_handler(
        request: Request,
        exc: PropertyNotFoundError,
    ) -> JSONResponse:
        """Handle PropertyNotFoundError exceptions."""
        logger.warning(
            "api.exception.property_not_found",
            property_id=str(exc.property_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "PROPERTY_NOT_FOUND",
                    "message": str(exc),
                    "property_id": str(exc.property_id),
                },
            },
        )

    @app.exception_handler(ValidationError)  # type: ignore[untyped-decorator]
    async def validation_error_handler(
        request: Request,
        exc: ValidationError,
    ) -> JSONResponse:
        """Handle ValidationError exceptions."""
        logger.warning(
            "api.exception.validation_error",
            field=exc.field,
            message=exc.message,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": exc.message,
                    "field": exc.field,
                    "details": exc.details,
                },
            },
        )

    @app.exception_handler(PydanticValidationError)  # type: ignore[untyped-decorator]
    async def pydantic_validation_error_handler(
        request: Request,
        exc: PydanticValidationError,
    ) -> JSONResponse:
        """Handle Pydantic ValidationError exceptions."""
        logger.warning(
            "api.exception.pydantic_validation_error",
            error_count=len(exc.errors()),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "details": exc.errors(),
                },
            },
        )

    # =========================================================================
    # Field Operations Exception Handlers (Phase 2)
    # =========================================================================

    @app.exception_handler(ServiceOfferingNotFoundError)  # type: ignore[untyped-decorator]
    async def service_offering_not_found_handler(
        request: Request,
        exc: ServiceOfferingNotFoundError,
    ) -> JSONResponse:
        """Handle ServiceOfferingNotFoundError exceptions."""
        logger.warning(
            "api.exception.service_offering_not_found",
            service_id=str(exc.service_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "SERVICE_OFFERING_NOT_FOUND",
                    "message": str(exc),
                    "service_id": str(exc.service_id),
                },
            },
        )

    @app.exception_handler(JobNotFoundError)  # type: ignore[untyped-decorator]
    async def job_not_found_handler(
        request: Request,
        exc: JobNotFoundError,
    ) -> JSONResponse:
        """Handle JobNotFoundError exceptions."""
        logger.warning(
            "api.exception.job_not_found",
            job_id=str(exc.job_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "JOB_NOT_FOUND",
                    "message": str(exc),
                    "job_id": str(exc.job_id),
                },
            },
        )

    @app.exception_handler(InvalidStatusTransitionError)  # type: ignore[untyped-decorator]
    async def invalid_status_transition_handler(
        request: Request,
        exc: InvalidStatusTransitionError,
    ) -> JSONResponse:
        """Handle InvalidStatusTransitionError exceptions."""
        logger.warning(
            "api.exception.invalid_status_transition",
            current_status=exc.current_status.value,
            requested_status=exc.requested_status.value,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_STATUS_TRANSITION",
                    "message": str(exc),
                    "current_status": exc.current_status.value,
                    "requested_status": exc.requested_status.value,
                },
            },
        )

    @app.exception_handler(StaffNotFoundError)  # type: ignore[untyped-decorator]
    async def staff_not_found_handler(
        request: Request,
        exc: StaffNotFoundError,
    ) -> JSONResponse:
        """Handle StaffNotFoundError exceptions."""
        logger.warning(
            "api.exception.staff_not_found",
            staff_id=str(exc.staff_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "STAFF_NOT_FOUND",
                    "message": str(exc),
                    "staff_id": str(exc.staff_id),
                },
            },
        )

    @app.exception_handler(PropertyCustomerMismatchError)  # type: ignore[untyped-decorator]
    async def property_customer_mismatch_handler(
        request: Request,
        exc: PropertyCustomerMismatchError,
    ) -> JSONResponse:
        """Handle PropertyCustomerMismatchError exceptions."""
        logger.warning(
            "api.exception.property_customer_mismatch",
            property_id=str(exc.property_id),
            customer_id=str(exc.customer_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "PROPERTY_CUSTOMER_MISMATCH",
                    "message": str(exc),
                    "property_id": str(exc.property_id),
                    "customer_id": str(exc.customer_id),
                },
            },
        )

    @app.exception_handler(ServiceOfferingInactiveError)  # type: ignore[untyped-decorator]
    async def service_offering_inactive_handler(
        request: Request,
        exc: ServiceOfferingInactiveError,
    ) -> JSONResponse:
        """Handle ServiceOfferingInactiveError exceptions."""
        logger.warning(
            "api.exception.service_offering_inactive",
            service_id=str(exc.service_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "SERVICE_OFFERING_INACTIVE",
                    "message": str(exc),
                    "service_id": str(exc.service_id),
                },
            },
        )

    # =========================================================================
    # Lead Capture Exception Handlers
    # =========================================================================

    @app.exception_handler(LeadNotFoundError)  # type: ignore[untyped-decorator]
    async def lead_not_found_handler(
        request: Request,
        exc: LeadNotFoundError,
    ) -> JSONResponse:
        """Handle LeadNotFoundError exceptions."""
        logger.warning(
            "api.exception.lead_not_found",
            lead_id=str(exc.lead_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "LEAD_NOT_FOUND",
                    "message": str(exc),
                    "lead_id": str(exc.lead_id),
                },
            },
        )

    @app.exception_handler(LeadAlreadyConvertedError)  # type: ignore[untyped-decorator]
    async def lead_already_converted_handler(
        request: Request,
        exc: LeadAlreadyConvertedError,
    ) -> JSONResponse:
        """Handle LeadAlreadyConvertedError exceptions."""
        logger.warning(
            "api.exception.lead_already_converted",
            lead_id=str(exc.lead_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "LEAD_ALREADY_CONVERTED",
                    "message": str(exc),
                    "lead_id": str(exc.lead_id),
                },
            },
        )

    @app.exception_handler(InvalidLeadStatusTransitionError)  # type: ignore[untyped-decorator]
    async def invalid_lead_status_transition_handler(
        request: Request,
        exc: InvalidLeadStatusTransitionError,
    ) -> JSONResponse:
        """Handle InvalidLeadStatusTransitionError exceptions."""
        logger.warning(
            "api.exception.invalid_lead_status_transition",
            current_status=exc.current_status.value,
            requested_status=exc.requested_status.value,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_LEAD_STATUS_TRANSITION",
                    "message": str(exc),
                    "current_status": exc.current_status.value,
                    "requested_status": exc.requested_status.value,
                },
            },
        )

    @app.exception_handler(DuplicateLeadError)  # type: ignore[untyped-decorator]
    async def duplicate_lead_handler(
        request: Request,
        exc: DuplicateLeadError,
    ) -> JSONResponse:
        """Handle DuplicateLeadError exceptions — HTTP 409."""
        logger.warning(
            "api.exception.duplicate_lead",
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": exc.detail,
                "message": exc.message,
            },
        )

    # =========================================================================
    # CRM Changes Update 2 — Domain-Specific Exception Handlers (Task 18.1)
    # =========================================================================

    @app.exception_handler(MergeBlockerError)  # type: ignore[untyped-decorator]
    async def merge_blocker_handler(
        request: Request,
        exc: MergeBlockerError,
    ) -> JSONResponse:
        """Handle MergeBlockerError — HTTP 409 Conflict.

        Validates: CRM Changes Update 2 Req 6.7
        """
        logger.warning(
            "api.exception.merge_blocker",
            message=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "error": {
                    "code": "MERGE_BLOCKER",
                    "message": str(exc),
                },
            },
        )

    @app.exception_handler(InvalidSalesTransitionError)  # type: ignore[untyped-decorator]
    async def invalid_sales_transition_handler(
        request: Request,
        exc: InvalidSalesTransitionError,
    ) -> JSONResponse:
        """Handle InvalidSalesTransitionError — HTTP 422 Unprocessable Entity.

        Validates: CRM Changes Update 2 Req 14.3
        """
        logger.warning(
            "api.exception.invalid_sales_transition",
            current_status=exc.current_status,
            target_status=exc.target_status,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "INVALID_SALES_TRANSITION",
                    "message": str(exc),
                    "current_status": exc.current_status,
                    "target_status": exc.target_status,
                },
            },
        )

    @app.exception_handler(SignWellDocumentNotFoundError)  # type: ignore[untyped-decorator]
    async def signwell_document_not_found_handler(
        request: Request,
        exc: SignWellDocumentNotFoundError,
    ) -> JSONResponse:
        """Handle SignWellDocumentNotFoundError — HTTP 404 Not Found.

        Validates: CRM Changes Update 2 Req 18.5
        """
        logger.warning(
            "api.exception.signwell_document_not_found",
            message=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "SIGNWELL_DOCUMENT_NOT_FOUND",
                    "message": str(exc),
                },
            },
        )

    @app.exception_handler(SignWellWebhookVerificationError)  # type: ignore[untyped-decorator]
    async def signwell_webhook_verification_handler(
        request: Request,
        exc: SignWellWebhookVerificationError,
    ) -> JSONResponse:
        """Handle SignWellWebhookVerificationError — HTTP 401 Unauthorized.

        Validates: CRM Changes Update 2 Req 18.5
        """
        logger.warning(
            "api.exception.signwell_webhook_verification_failed",
            message=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "error": {
                    "code": "SIGNWELL_WEBHOOK_VERIFICATION_FAILED",
                    "message": "Webhook signature verification failed",
                },
            },
        )

    @app.exception_handler(SignWellError)  # type: ignore[untyped-decorator]
    async def signwell_error_handler(
        request: Request,
        exc: SignWellError,
    ) -> JSONResponse:
        """Handle SignWellError — HTTP 502 Bad Gateway.

        Validates: CRM Changes Update 2 Req 18.5
        """
        logger.error(
            "api.exception.signwell_error",
            message=str(exc),
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={
                "success": False,
                "error": {
                    "code": "SIGNWELL_ERROR",
                    "message": "E-signature service error",
                },
            },
        )

    @app.exception_handler(ConfirmationCorrelationError)  # type: ignore[untyped-decorator]
    async def confirmation_correlation_handler(
        request: Request,
        exc: ConfirmationCorrelationError,
    ) -> JSONResponse:
        """Handle ConfirmationCorrelationError — HTTP 404 Not Found."""
        logger.warning(
            "api.exception.confirmation_correlation_failed",
            thread_id=exc.thread_id,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "CONFIRMATION_CORRELATION_ERROR",
                    "message": str(exc),
                    "thread_id": exc.thread_id,
                },
            },
        )

    @app.exception_handler(RenewalProposalNotFoundError)  # type: ignore[untyped-decorator]
    async def renewal_proposal_not_found_handler(
        request: Request,
        exc: RenewalProposalNotFoundError,
    ) -> JSONResponse:
        """Handle RenewalProposalNotFoundError — HTTP 404 Not Found."""
        logger.warning(
            "api.exception.renewal_proposal_not_found",
            proposal_id=str(exc.proposal_id),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "RENEWAL_PROPOSAL_NOT_FOUND",
                    "message": str(exc),
                    "proposal_id": str(exc.proposal_id),
                },
            },
        )

    @app.exception_handler(DocumentUploadError)  # type: ignore[untyped-decorator]
    async def document_upload_error_handler(
        request: Request,
        exc: DocumentUploadError,
    ) -> JSONResponse:
        """Handle DocumentUploadError — HTTP 400 Bad Request."""
        logger.warning(
            "api.exception.document_upload_error",
            message=str(exc),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "DOCUMENT_UPLOAD_ERROR",
                    "message": str(exc),
                },
            },
        )

    @app.exception_handler(WebAuthnVerificationError)  # type: ignore[untyped-decorator]
    async def webauthn_verification_handler(
        request: Request,
        exc: WebAuthnVerificationError,
    ) -> JSONResponse:
        """Handle WebAuthnVerificationError — HTTP 401 Unauthorized."""
        logger.warning(
            "api.exception.webauthn_verification_failed",
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "success": False,
                "error": {
                    "code": "WEBAUTHN_VERIFICATION_FAILED",
                    "message": str(exc) or "Authentication failed",
                },
            },
        )

    @app.exception_handler(WebAuthnChallengeNotFoundError)  # type: ignore[untyped-decorator]
    async def webauthn_challenge_not_found_handler(
        request: Request,
        exc: WebAuthnChallengeNotFoundError,
    ) -> JSONResponse:
        """Handle WebAuthnChallengeNotFoundError — HTTP 400 Bad Request."""
        logger.warning(
            "api.exception.webauthn_challenge_not_found",
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "success": False,
                "error": {
                    "code": "WEBAUTHN_CHALLENGE_NOT_FOUND",
                    "message": str(exc) or "Challenge expired or invalid",
                },
            },
        )

    @app.exception_handler(WebAuthnCredentialNotFoundError)  # type: ignore[untyped-decorator]
    async def webauthn_credential_not_found_handler(
        request: Request,
        exc: WebAuthnCredentialNotFoundError,
    ) -> JSONResponse:
        """Handle WebAuthnCredentialNotFoundError — HTTP 404 Not Found."""
        logger.warning(
            "api.exception.webauthn_credential_not_found",
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "success": False,
                "error": {
                    "code": "WEBAUTHN_CREDENTIAL_NOT_FOUND",
                    "message": str(exc) or "Passkey not found",
                },
            },
        )

    @app.exception_handler(WebAuthnDuplicateCredentialError)  # type: ignore[untyped-decorator]
    async def webauthn_duplicate_credential_handler(
        request: Request,
        exc: WebAuthnDuplicateCredentialError,
    ) -> JSONResponse:
        """Handle WebAuthnDuplicateCredentialError — HTTP 409 Conflict."""
        logger.warning(
            "api.exception.webauthn_duplicate_credential",
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "success": False,
                "error": {
                    "code": "WEBAUTHN_DUPLICATE_CREDENTIAL",
                    "message": str(exc) or "Passkey already registered",
                },
            },
        )

    @app.exception_handler(Exception)  # type: ignore[untyped-decorator]
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Last-resort handler so 5xx responses carry CORS headers.

        Without this, Starlette's ServerErrorMiddleware emits the response
        outside CORSMiddleware and the browser sees an opaque CORS error
        instead of the real 500. (bughunt 2026-04-28 §Bug 4.)
        """
        logger.error(
            "api.exception.unhandled",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_type=type(exc).__name__,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                },
            },
        )


# Create the application instance
app = create_app()
