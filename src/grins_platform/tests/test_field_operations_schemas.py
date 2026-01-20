"""
Tests for Field Operations Pydantic schemas.

This module tests all Pydantic schemas for Phase 2 Field Operations,
including service offerings, jobs, and staff schemas.

Validates: Requirements 1.1-1.13, 2.1-2.12, 4.1-4.10, 5.1-5.7, 6.1-6.9,
8.1-8.10, 9.1-9.5
"""

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from grins_platform.models.enums import (
    JobCategory,
    JobSource,
    JobStatus,
    PricingModel,
    ServiceCategory,
    SkillLevel,
    StaffRole,
)
from grins_platform.schemas.job import (
    JobCreate,
    JobListParams,
    JobResponse,
    JobStatusHistoryResponse,
    JobStatusUpdate,
    JobUpdate,
    PaginatedJobResponse,
    PriceCalculationResponse,
)
from grins_platform.schemas.service_offering import (
    PaginatedServiceResponse,
    ServiceListParams,
    ServiceOfferingCreate,
    ServiceOfferingResponse,
    ServiceOfferingUpdate,
)
from grins_platform.schemas.staff import (
    PaginatedStaffResponse,
    StaffAvailabilityUpdate,
    StaffCreate,
    StaffListParams,
    StaffResponse,
    StaffUpdate,
)

# =============================================================================
# Service Offering Schema Tests
# =============================================================================


@pytest.mark.unit
class TestServiceOfferingCreate:
    """Tests for ServiceOfferingCreate schema."""

    def test_valid_service_offering_create(self) -> None:
        """Test creating a valid service offering."""
        data = ServiceOfferingCreate(
            name="Spring Startup",
            category=ServiceCategory.SEASONAL,
            pricing_model=PricingModel.ZONE_BASED,
            base_price=Decimal("50.00"),
            price_per_zone=Decimal("10.00"),
        )
        assert data.name == "Spring Startup"
        assert data.category == ServiceCategory.SEASONAL
        assert data.pricing_model == PricingModel.ZONE_BASED

    def test_name_whitespace_stripped(self) -> None:
        """Test that name whitespace is stripped."""
        data = ServiceOfferingCreate(
            name="  Spring Startup  ",
            category=ServiceCategory.SEASONAL,
            pricing_model=PricingModel.FLAT,
        )
        assert data.name == "Spring Startup"

    def test_name_required(self) -> None:
        """Test that name is required."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceOfferingCreate(
                category=ServiceCategory.SEASONAL,
                pricing_model=PricingModel.FLAT,
            )
        assert "name" in str(exc_info.value)

    def test_name_min_length(self) -> None:
        """Test name minimum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceOfferingCreate(
                name="",
                category=ServiceCategory.SEASONAL,
                pricing_model=PricingModel.FLAT,
            )
        assert "name" in str(exc_info.value)

    def test_name_max_length(self) -> None:
        """Test name maximum length validation."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceOfferingCreate(
                name="x" * 101,
                category=ServiceCategory.SEASONAL,
                pricing_model=PricingModel.FLAT,
            )
        assert "name" in str(exc_info.value)

    def test_category_enum_validation(self) -> None:
        """Test category enum validation."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceOfferingCreate(
                name="Test",
                category="invalid_category",  # type: ignore
                pricing_model=PricingModel.FLAT,
            )
        assert "category" in str(exc_info.value)

    def test_pricing_model_enum_validation(self) -> None:
        """Test pricing model enum validation."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceOfferingCreate(
                name="Test",
                category=ServiceCategory.SEASONAL,
                pricing_model="invalid_model",  # type: ignore
            )
        assert "pricing_model" in str(exc_info.value)

    def test_base_price_non_negative(self) -> None:
        """Test base price must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceOfferingCreate(
                name="Test",
                category=ServiceCategory.SEASONAL,
                pricing_model=PricingModel.FLAT,
                base_price=Decimal("-10.00"),
            )
        assert "base_price" in str(exc_info.value)

    def test_price_per_zone_non_negative(self) -> None:
        """Test price per zone must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceOfferingCreate(
                name="Test",
                category=ServiceCategory.SEASONAL,
                pricing_model=PricingModel.ZONE_BASED,
                price_per_zone=Decimal("-5.00"),
            )
        assert "price_per_zone" in str(exc_info.value)

    def test_estimated_duration_positive(self) -> None:
        """Test estimated duration must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceOfferingCreate(
                name="Test",
                category=ServiceCategory.SEASONAL,
                pricing_model=PricingModel.FLAT,
                estimated_duration_minutes=0,
            )
        assert "estimated_duration_minutes" in str(exc_info.value)

    def test_staffing_required_minimum(self) -> None:
        """Test staffing required minimum is 1."""
        with pytest.raises(ValidationError) as exc_info:
            ServiceOfferingCreate(
                name="Test",
                category=ServiceCategory.SEASONAL,
                pricing_model=PricingModel.FLAT,
                staffing_required=0,
            )
        assert "staffing_required" in str(exc_info.value)

    def test_defaults_applied(self) -> None:
        """Test default values are applied."""
        data = ServiceOfferingCreate(
            name="Test",
            category=ServiceCategory.SEASONAL,
            pricing_model=PricingModel.FLAT,
        )
        assert data.staffing_required == 1
        assert data.lien_eligible is False
        assert data.requires_prepay is False


@pytest.mark.unit
class TestServiceOfferingUpdate:
    """Tests for ServiceOfferingUpdate schema."""

    def test_all_fields_optional(self) -> None:
        """Test all fields are optional."""
        data = ServiceOfferingUpdate()
        assert data.name is None
        assert data.category is None

    def test_partial_update(self) -> None:
        """Test partial update with some fields."""
        data = ServiceOfferingUpdate(
            name="Updated Name",
            base_price=Decimal("75.00"),
        )
        assert data.name == "Updated Name"
        assert data.base_price == Decimal("75.00")
        assert data.category is None


@pytest.mark.unit
class TestServiceOfferingResponse:
    """Tests for ServiceOfferingResponse schema."""

    def test_from_attributes(self) -> None:
        """Test creating response from model attributes."""
        now = datetime.now()
        data = ServiceOfferingResponse(
            id=uuid4(),
            name="Test Service",
            category=ServiceCategory.SEASONAL,
            pricing_model=PricingModel.FLAT,
            staffing_required=1,
            lien_eligible=False,
            requires_prepay=False,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert data.name == "Test Service"
        assert data.category == ServiceCategory.SEASONAL

    def test_category_string_conversion(self) -> None:
        """Test category string is converted to enum."""
        now = datetime.now()
        data = ServiceOfferingResponse(
            id=uuid4(),
            name="Test",
            category="seasonal",  # type: ignore
            pricing_model="flat",  # type: ignore
            staffing_required=1,
            lien_eligible=False,
            requires_prepay=False,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert data.category == ServiceCategory.SEASONAL
        assert data.pricing_model == PricingModel.FLAT


@pytest.mark.unit
class TestServiceListParams:
    """Tests for ServiceListParams schema."""

    def test_defaults(self) -> None:
        """Test default values."""
        params = ServiceListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort_by == "name"
        assert params.sort_order == "asc"

    def test_page_minimum(self) -> None:
        """Test page minimum is 1."""
        with pytest.raises(ValidationError):
            ServiceListParams(page=0)

    def test_page_size_maximum(self) -> None:
        """Test page size maximum is 100."""
        with pytest.raises(ValidationError):
            ServiceListParams(page_size=101)

    def test_sort_order_validation(self) -> None:
        """Test sort order must be asc or desc."""
        with pytest.raises(ValidationError):
            ServiceListParams(sort_order="invalid")


# =============================================================================
# Job Schema Tests
# =============================================================================


@pytest.mark.unit
class TestJobCreate:
    """Tests for JobCreate schema."""

    def test_valid_job_create(self) -> None:
        """Test creating a valid job."""
        customer_id = uuid4()
        data = JobCreate(
            customer_id=customer_id,
            job_type="spring_startup",
        )
        assert data.customer_id == customer_id
        assert data.job_type == "spring_startup"

    def test_job_type_normalized(self) -> None:
        """Test job type is stripped and lowercased."""
        data = JobCreate(
            customer_id=uuid4(),
            job_type="  Spring_Startup  ",
        )
        assert data.job_type == "spring_startup"

    def test_customer_id_required(self) -> None:
        """Test customer_id is required."""
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(job_type="repair")
        assert "customer_id" in str(exc_info.value)

    def test_job_type_required(self) -> None:
        """Test job_type is required."""
        with pytest.raises(ValidationError) as exc_info:
            JobCreate(customer_id=uuid4())
        assert "job_type" in str(exc_info.value)

    def test_priority_level_range(self) -> None:
        """Test priority level must be 0-2."""
        with pytest.raises(ValidationError):
            JobCreate(
                customer_id=uuid4(),
                job_type="repair",
                priority_level=3,
            )

    def test_quoted_amount_non_negative(self) -> None:
        """Test quoted amount must be non-negative."""
        with pytest.raises(ValidationError):
            JobCreate(
                customer_id=uuid4(),
                job_type="repair",
                quoted_amount=Decimal("-100.00"),
            )

    def test_source_enum_validation(self) -> None:
        """Test source enum validation."""
        with pytest.raises(ValidationError):
            JobCreate(
                customer_id=uuid4(),
                job_type="repair",
                source="invalid_source",  # type: ignore
            )

    def test_defaults_applied(self) -> None:
        """Test default values are applied."""
        data = JobCreate(
            customer_id=uuid4(),
            job_type="repair",
        )
        assert data.priority_level == 0
        assert data.weather_sensitive is False
        assert data.staffing_required == 1


@pytest.mark.unit
class TestJobUpdate:
    """Tests for JobUpdate schema."""

    def test_all_fields_optional(self) -> None:
        """Test all fields are optional."""
        data = JobUpdate()
        assert data.job_type is None
        assert data.category is None

    def test_category_enum_validation(self) -> None:
        """Test category enum validation."""
        with pytest.raises(ValidationError):
            JobUpdate(category="invalid_category")  # type: ignore


@pytest.mark.unit
class TestJobStatusUpdate:
    """Tests for JobStatusUpdate schema."""

    def test_valid_status_update(self) -> None:
        """Test valid status update."""
        data = JobStatusUpdate(
            status=JobStatus.APPROVED,
            notes="Approved by manager",
        )
        assert data.status == JobStatus.APPROVED
        assert data.notes == "Approved by manager"

    def test_status_required(self) -> None:
        """Test status is required."""
        with pytest.raises(ValidationError):
            JobStatusUpdate()

    def test_status_enum_validation(self) -> None:
        """Test status enum validation."""
        with pytest.raises(ValidationError):
            JobStatusUpdate(status="invalid_status")  # type: ignore


@pytest.mark.unit
class TestJobResponse:
    """Tests for JobResponse schema."""

    def test_from_attributes(self) -> None:
        """Test creating response from model attributes."""
        now = datetime.now()
        data = JobResponse(
            id=uuid4(),
            customer_id=uuid4(),
            job_type="repair",
            category=JobCategory.READY_TO_SCHEDULE,
            status=JobStatus.REQUESTED,
            priority_level=0,
            weather_sensitive=False,
            staffing_required=1,
            created_at=now,
            updated_at=now,
        )
        assert data.job_type == "repair"
        assert data.category == JobCategory.READY_TO_SCHEDULE

    def test_enum_string_conversion(self) -> None:
        """Test enum strings are converted."""
        now = datetime.now()
        data = JobResponse(
            id=uuid4(),
            customer_id=uuid4(),
            job_type="repair",
            category="ready_to_schedule",  # type: ignore
            status="requested",  # type: ignore
            source="website",  # type: ignore
            priority_level=0,
            weather_sensitive=False,
            staffing_required=1,
            created_at=now,
            updated_at=now,
        )
        assert data.category == JobCategory.READY_TO_SCHEDULE
        assert data.status == JobStatus.REQUESTED
        assert data.source == JobSource.WEBSITE


@pytest.mark.unit
class TestJobStatusHistoryResponse:
    """Tests for JobStatusHistoryResponse schema."""

    def test_valid_history_response(self) -> None:
        """Test valid history response."""
        now = datetime.now()
        data = JobStatusHistoryResponse(
            id=uuid4(),
            job_id=uuid4(),
            previous_status=JobStatus.REQUESTED,
            new_status=JobStatus.APPROVED,
            changed_at=now,
        )
        assert data.previous_status == JobStatus.REQUESTED
        assert data.new_status == JobStatus.APPROVED

    def test_previous_status_nullable(self) -> None:
        """Test previous status can be null (initial status)."""
        now = datetime.now()
        data = JobStatusHistoryResponse(
            id=uuid4(),
            job_id=uuid4(),
            previous_status=None,
            new_status=JobStatus.REQUESTED,
            changed_at=now,
        )
        assert data.previous_status is None


@pytest.mark.unit
class TestPriceCalculationResponse:
    """Tests for PriceCalculationResponse schema."""

    def test_valid_calculation_response(self) -> None:
        """Test valid price calculation response."""
        data = PriceCalculationResponse(
            job_id=uuid4(),
            service_offering_id=uuid4(),
            pricing_model=PricingModel.ZONE_BASED,
            base_price=Decimal("50.00"),
            zone_count=5,
            calculated_price=Decimal("100.00"),
            requires_manual_quote=False,
            calculation_details={"formula": "base + (zones * per_zone)"},
        )
        assert data.calculated_price == Decimal("100.00")
        assert data.requires_manual_quote is False

    def test_requires_manual_quote(self) -> None:
        """Test response when manual quote is required."""
        data = PriceCalculationResponse(
            job_id=uuid4(),
            pricing_model=PricingModel.CUSTOM,
            requires_manual_quote=True,
            calculated_price=None,
        )
        assert data.requires_manual_quote is True
        assert data.calculated_price is None


@pytest.mark.unit
class TestJobListParams:
    """Tests for JobListParams schema."""

    def test_defaults(self) -> None:
        """Test default values."""
        params = JobListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort_by == "created_at"
        assert params.sort_order == "desc"

    def test_all_filters(self) -> None:
        """Test all filter parameters."""
        customer_id = uuid4()
        params = JobListParams(
            status=JobStatus.REQUESTED,
            category=JobCategory.READY_TO_SCHEDULE,
            customer_id=customer_id,
            priority_level=1,
        )
        assert params.status == JobStatus.REQUESTED
        assert params.category == JobCategory.READY_TO_SCHEDULE
        assert params.customer_id == customer_id
        assert params.priority_level == 1


# =============================================================================
# Staff Schema Tests
# =============================================================================


@pytest.mark.unit
class TestStaffCreate:
    """Tests for StaffCreate schema."""

    def test_valid_staff_create(self) -> None:
        """Test creating a valid staff member."""
        data = StaffCreate(
            name="John Doe",
            phone="6125551234",
            role=StaffRole.TECH,
        )
        assert data.name == "John Doe"
        assert data.phone == "6125551234"
        assert data.role == StaffRole.TECH

    def test_phone_normalization(self) -> None:
        """Test phone number is normalized."""
        data = StaffCreate(
            name="John Doe",
            phone="(612) 555-1234",
            role=StaffRole.TECH,
        )
        assert data.phone == "6125551234"

    def test_name_whitespace_stripped(self) -> None:
        """Test name whitespace is stripped."""
        data = StaffCreate(
            name="  John Doe  ",
            phone="6125551234",
            role=StaffRole.TECH,
        )
        assert data.name == "John Doe"

    def test_name_required(self) -> None:
        """Test name is required."""
        with pytest.raises(ValidationError):
            StaffCreate(
                phone="6125551234",
                role=StaffRole.TECH,
            )

    def test_phone_required(self) -> None:
        """Test phone is required."""
        with pytest.raises(ValidationError):
            StaffCreate(
                name="John Doe",
                role=StaffRole.TECH,
            )

    def test_role_required(self) -> None:
        """Test role is required."""
        with pytest.raises(ValidationError):
            StaffCreate(
                name="John Doe",
                phone="6125551234",
            )

    def test_role_enum_validation(self) -> None:
        """Test role enum validation."""
        with pytest.raises(ValidationError):
            StaffCreate(
                name="John Doe",
                phone="6125551234",
                role="invalid_role",  # type: ignore
            )

    def test_skill_level_enum_validation(self) -> None:
        """Test skill level enum validation."""
        with pytest.raises(ValidationError):
            StaffCreate(
                name="John Doe",
                phone="6125551234",
                role=StaffRole.TECH,
                skill_level="invalid_level",  # type: ignore
            )

    def test_hourly_rate_non_negative(self) -> None:
        """Test hourly rate must be non-negative."""
        with pytest.raises(ValidationError):
            StaffCreate(
                name="John Doe",
                phone="6125551234",
                role=StaffRole.TECH,
                hourly_rate=Decimal("-25.00"),
            )

    def test_phone_invalid_length(self) -> None:
        """Test phone must be 10 digits."""
        with pytest.raises(ValidationError):
            StaffCreate(
                name="John Doe",
                phone="123456789",  # 9 digits
                role=StaffRole.TECH,
            )

    def test_defaults_applied(self) -> None:
        """Test default values are applied."""
        data = StaffCreate(
            name="John Doe",
            phone="6125551234",
            role=StaffRole.TECH,
        )
        assert data.is_available is True


@pytest.mark.unit
class TestStaffUpdate:
    """Tests for StaffUpdate schema."""

    def test_all_fields_optional(self) -> None:
        """Test all fields are optional."""
        data = StaffUpdate()
        assert data.name is None
        assert data.phone is None
        assert data.role is None

    def test_phone_normalization(self) -> None:
        """Test phone is normalized when provided."""
        data = StaffUpdate(phone="(612) 555-9999")
        assert data.phone == "6125559999"


@pytest.mark.unit
class TestStaffAvailabilityUpdate:
    """Tests for StaffAvailabilityUpdate schema."""

    def test_valid_availability_update(self) -> None:
        """Test valid availability update."""
        data = StaffAvailabilityUpdate(
            is_available=False,
            availability_notes="On vacation until next week",
        )
        assert data.is_available is False
        assert data.availability_notes == "On vacation until next week"

    def test_is_available_required(self) -> None:
        """Test is_available is required."""
        with pytest.raises(ValidationError):
            StaffAvailabilityUpdate()


@pytest.mark.unit
class TestStaffResponse:
    """Tests for StaffResponse schema."""

    def test_from_attributes(self) -> None:
        """Test creating response from model attributes."""
        now = datetime.now()
        data = StaffResponse(
            id=uuid4(),
            name="John Doe",
            phone="6125551234",
            role=StaffRole.TECH,
            is_available=True,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert data.name == "John Doe"
        assert data.role == StaffRole.TECH

    def test_enum_string_conversion(self) -> None:
        """Test enum strings are converted."""
        now = datetime.now()
        data = StaffResponse(
            id=uuid4(),
            name="John Doe",
            phone="6125551234",
            role="tech",  # type: ignore
            skill_level="senior",  # type: ignore
            is_available=True,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        assert data.role == StaffRole.TECH
        assert data.skill_level == SkillLevel.SENIOR


@pytest.mark.unit
class TestStaffListParams:
    """Tests for StaffListParams schema."""

    def test_defaults(self) -> None:
        """Test default values."""
        params = StaffListParams()
        assert params.page == 1
        assert params.page_size == 20
        assert params.sort_by == "name"
        assert params.sort_order == "asc"

    def test_all_filters(self) -> None:
        """Test all filter parameters."""
        params = StaffListParams(
            role=StaffRole.TECH,
            skill_level=SkillLevel.SENIOR,
            is_available=True,
            is_active=True,
        )
        assert params.role == StaffRole.TECH
        assert params.skill_level == SkillLevel.SENIOR
        assert params.is_available is True
        assert params.is_active is True


# =============================================================================
# Paginated Response Tests
# =============================================================================


@pytest.mark.unit
class TestPaginatedResponses:
    """Tests for paginated response schemas."""

    def test_paginated_service_response(self) -> None:
        """Test PaginatedServiceResponse."""
        data = PaginatedServiceResponse(
            items=[],
            total=0,
            page=1,
            page_size=20,
            total_pages=0,
        )
        assert data.total == 0
        assert data.total_pages == 0

    def test_paginated_job_response(self) -> None:
        """Test PaginatedJobResponse."""
        data = PaginatedJobResponse(
            items=[],
            total=50,
            page=2,
            page_size=20,
            total_pages=3,
        )
        assert data.total == 50
        assert data.page == 2
        assert data.total_pages == 3

    def test_paginated_staff_response(self) -> None:
        """Test PaginatedStaffResponse."""
        data = PaginatedStaffResponse(
            items=[],
            total=10,
            page=1,
            page_size=20,
            total_pages=1,
        )
        assert data.total == 10
        assert data.total_pages == 1


# =============================================================================
# Property-Based Test: Enum Validation Completeness (Property 2)
# =============================================================================


@pytest.mark.unit
class TestEnumValidationCompleteness:
    """Property 2: Enum Validation Completeness.

    All enum fields must reject invalid values and accept all valid enum values.
    """

    def test_all_service_categories_accepted(self) -> None:
        """Test all ServiceCategory values are accepted."""
        for category in ServiceCategory:
            data = ServiceOfferingCreate(
                name="Test",
                category=category,
                pricing_model=PricingModel.FLAT,
            )
            assert data.category == category

    def test_all_pricing_models_accepted(self) -> None:
        """Test all PricingModel values are accepted."""
        for model in PricingModel:
            data = ServiceOfferingCreate(
                name="Test",
                category=ServiceCategory.SEASONAL,
                pricing_model=model,
            )
            assert data.pricing_model == model

    def test_all_job_statuses_accepted(self) -> None:
        """Test all JobStatus values are accepted."""
        for status in JobStatus:
            data = JobStatusUpdate(status=status)
            assert data.status == status

    def test_all_job_categories_accepted(self) -> None:
        """Test all JobCategory values are accepted."""
        for category in JobCategory:
            data = JobUpdate(category=category)
            assert data.category == category

    def test_all_job_sources_accepted(self) -> None:
        """Test all JobSource values are accepted."""
        for source in JobSource:
            data = JobCreate(
                customer_id=uuid4(),
                job_type="test",
                source=source,
            )
            assert data.source == source

    def test_all_staff_roles_accepted(self) -> None:
        """Test all StaffRole values are accepted."""
        for role in StaffRole:
            data = StaffCreate(
                name="Test",
                phone="6125551234",
                role=role,
            )
            assert data.role == role

    def test_all_skill_levels_accepted(self) -> None:
        """Test all SkillLevel values are accepted."""
        for level in SkillLevel:
            data = StaffCreate(
                name="Test",
                phone="6125551234",
                role=StaffRole.TECH,
                skill_level=level,
            )
            assert data.skill_level == level
