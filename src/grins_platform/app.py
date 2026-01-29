"""
FastAPI application factory and configuration.

This module creates and configures the FastAPI application instance
with all routers, middleware, and exception handlers.

Validates: Requirement 10.5-10.7
"""

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
    CustomerNotFoundError,
    DuplicateCustomerError,
    InvalidStatusTransitionError,
    JobNotFoundError,
    PropertyCustomerMismatchError,
    PropertyNotFoundError,
    ServiceOfferingInactiveError,
    ServiceOfferingNotFoundError,
    StaffNotFoundError,
    ValidationError,
)
from grins_platform.log_config import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001 - Required by FastAPI lifespan protocol
    """Application lifespan manager for startup and shutdown events.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    logger.info("app.startup_started", version="1.0.0")
    db_manager = get_database_manager()
    health = await db_manager.health_check()
    logger.info("app.startup_database_check", **health)
    logger.info("app.startup_completed")

    yield

    # Shutdown
    logger.info("app.shutdown_started")
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

    # Configure CORS - must specify explicit origins when using credentials
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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


# Create the application instance
app = create_app()
