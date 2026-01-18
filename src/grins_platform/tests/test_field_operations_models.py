"""
Tests for Field Operations models.

This module contains tests for ServiceOffering, Job, JobStatusHistory,
and Staff models.

Validates: Requirements 1.1-1.13, 2.1-2.12, 4.1-4.10, 7.1-7.4, 8.1-8.10
"""

from decimal import Decimal

from grins_platform.models import (
    Job,
    JobCategory,
    JobSource,
    JobStatus,
    JobStatusHistory,
    PricingModel,
    ServiceCategory,
    ServiceOffering,
    SkillLevel,
    Staff,
    StaffRole,
)
from grins_platform.models.job import VALID_STATUS_TRANSITIONS

# =============================================================================
# Phase 2 Enum Tests
# =============================================================================


class TestServiceCategory:
    """Tests for ServiceCategory enum."""

    def test_all_values(self) -> None:
        """Test all service category values exist."""
        assert ServiceCategory.SEASONAL.value == "seasonal"
        assert ServiceCategory.REPAIR.value == "repair"
        assert ServiceCategory.INSTALLATION.value == "installation"
        assert ServiceCategory.DIAGNOSTIC.value == "diagnostic"
        assert ServiceCategory.LANDSCAPING.value == "landscaping"

    def test_enum_from_string(self) -> None:
        """Test creating enum from string value."""
        assert ServiceCategory("seasonal") == ServiceCategory.SEASONAL
        assert ServiceCategory("repair") == ServiceCategory.REPAIR


class TestPricingModel:
    """Tests for PricingModel enum."""

    def test_all_values(self) -> None:
        """Test all pricing model values exist."""
        assert PricingModel.FLAT.value == "flat"
        assert PricingModel.ZONE_BASED.value == "zone_based"
        assert PricingModel.HOURLY.value == "hourly"
        assert PricingModel.CUSTOM.value == "custom"


class TestJobCategory:
    """Tests for JobCategory enum."""

    def test_all_values(self) -> None:
        """Test all job category values exist."""
        assert JobCategory.READY_TO_SCHEDULE.value == "ready_to_schedule"
        assert JobCategory.REQUIRES_ESTIMATE.value == "requires_estimate"


class TestJobStatus:
    """Tests for JobStatus enum."""

    def test_all_values(self) -> None:
        """Test all job status values exist."""
        assert JobStatus.REQUESTED.value == "requested"
        assert JobStatus.APPROVED.value == "approved"
        assert JobStatus.SCHEDULED.value == "scheduled"
        assert JobStatus.IN_PROGRESS.value == "in_progress"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.CANCELLED.value == "cancelled"
        assert JobStatus.CLOSED.value == "closed"


class TestJobSource:
    """Tests for JobSource enum."""

    def test_all_values(self) -> None:
        """Test all job source values exist."""
        assert JobSource.WEBSITE.value == "website"
        assert JobSource.GOOGLE.value == "google"
        assert JobSource.REFERRAL.value == "referral"
        assert JobSource.PHONE.value == "phone"
        assert JobSource.PARTNER.value == "partner"


class TestStaffRole:
    """Tests for StaffRole enum."""

    def test_all_values(self) -> None:
        """Test all staff role values exist."""
        assert StaffRole.TECH.value == "tech"
        assert StaffRole.SALES.value == "sales"
        assert StaffRole.ADMIN.value == "admin"


class TestSkillLevel:
    """Tests for SkillLevel enum."""

    def test_all_values(self) -> None:
        """Test all skill level values exist."""
        assert SkillLevel.JUNIOR.value == "junior"
        assert SkillLevel.SENIOR.value == "senior"
        assert SkillLevel.LEAD.value == "lead"


# =============================================================================
# ServiceOffering Model Tests
# =============================================================================


class TestServiceOfferingModel:
    """Tests for ServiceOffering model."""

    def test_tablename(self) -> None:
        """Test ServiceOffering table name."""
        assert ServiceOffering.__tablename__ == "service_offerings"

    def test_category_enum_property(self) -> None:
        """Test category_enum property returns correct enum."""
        service = ServiceOffering()
        service.category = "seasonal"
        assert service.category_enum == ServiceCategory.SEASONAL

    def test_pricing_model_enum_property(self) -> None:
        """Test pricing_model_enum property returns correct enum."""
        service = ServiceOffering()
        service.pricing_model = "zone_based"
        assert service.pricing_model_enum == PricingModel.ZONE_BASED

    def test_to_dict(self) -> None:
        """Test to_dict method returns correct dictionary."""
        service = ServiceOffering()
        service.name = "Spring Startup"
        service.category = "seasonal"
        service.pricing_model = "zone_based"
        service.base_price = Decimal("75.00")
        service.price_per_zone = Decimal("5.00")
        service.is_active = True

        result = service.to_dict()

        assert result["name"] == "Spring Startup"
        assert result["category"] == "seasonal"
        assert result["pricing_model"] == "zone_based"
        assert result["base_price"] == 75.00
        assert result["price_per_zone"] == 5.00
        assert result["is_active"] is True

    def test_repr(self) -> None:
        """Test __repr__ method."""
        service = ServiceOffering()
        service.name = "Test Service"
        service.category = "repair"

        repr_str = repr(service)

        assert "ServiceOffering" in repr_str
        assert "Test Service" in repr_str
        assert "repair" in repr_str


# =============================================================================
# Job Model Tests
# =============================================================================


class TestJobModel:
    """Tests for Job model."""

    def test_tablename(self) -> None:
        """Test Job table name."""
        assert Job.__tablename__ == "jobs"

    def test_status_enum_property(self) -> None:
        """Test status_enum property returns correct enum."""
        job = Job()
        job.status = "requested"
        assert job.status_enum == JobStatus.REQUESTED

    def test_category_enum_property(self) -> None:
        """Test category_enum property returns correct enum."""
        job = Job()
        job.category = "ready_to_schedule"
        assert job.category_enum == JobCategory.READY_TO_SCHEDULE

    def test_source_enum_property_with_value(self) -> None:
        """Test source_enum property returns correct enum when set."""
        job = Job()
        job.source = "partner"
        assert job.source_enum == JobSource.PARTNER

    def test_source_enum_property_none(self) -> None:
        """Test source_enum property returns None when not set."""
        job = Job()
        job.source = None
        assert job.source_enum is None

    def test_can_transition_to_valid(self) -> None:
        """Test can_transition_to returns True for valid transitions."""
        job = Job()
        job.status = "requested"
        assert job.can_transition_to("approved") is True
        assert job.can_transition_to("cancelled") is True

    def test_can_transition_to_invalid(self) -> None:
        """Test can_transition_to returns False for invalid transitions."""
        job = Job()
        job.status = "requested"
        assert job.can_transition_to("completed") is False
        assert job.can_transition_to("closed") is False

    def test_get_valid_transitions(self) -> None:
        """Test get_valid_transitions returns correct list."""
        job = Job()
        job.status = "approved"
        transitions = job.get_valid_transitions()
        assert "scheduled" in transitions
        assert "cancelled" in transitions
        assert len(transitions) == 2

    def test_is_terminal_status_cancelled(self) -> None:
        """Test is_terminal_status returns True for cancelled."""
        job = Job()
        job.status = "cancelled"
        assert job.is_terminal_status() is True

    def test_is_terminal_status_closed(self) -> None:
        """Test is_terminal_status returns True for closed."""
        job = Job()
        job.status = "closed"
        assert job.is_terminal_status() is True

    def test_is_terminal_status_in_progress(self) -> None:
        """Test is_terminal_status returns False for non-terminal status."""
        job = Job()
        job.status = "in_progress"
        assert job.is_terminal_status() is False

    def test_repr(self) -> None:
        """Test __repr__ method."""
        job = Job()
        job.job_type = "spring_startup"
        job.status = "requested"

        repr_str = repr(job)

        assert "Job" in repr_str
        assert "spring_startup" in repr_str
        assert "requested" in repr_str


class TestValidStatusTransitions:
    """Tests for VALID_STATUS_TRANSITIONS constant."""

    def test_requested_transitions(self) -> None:
        """Test valid transitions from requested status."""
        transitions = VALID_STATUS_TRANSITIONS["requested"]
        assert "approved" in transitions
        assert "cancelled" in transitions
        assert len(transitions) == 2

    def test_approved_transitions(self) -> None:
        """Test valid transitions from approved status."""
        transitions = VALID_STATUS_TRANSITIONS["approved"]
        assert "scheduled" in transitions
        assert "cancelled" in transitions
        assert len(transitions) == 2

    def test_scheduled_transitions(self) -> None:
        """Test valid transitions from scheduled status."""
        transitions = VALID_STATUS_TRANSITIONS["scheduled"]
        assert "in_progress" in transitions
        assert "cancelled" in transitions
        assert len(transitions) == 2

    def test_in_progress_transitions(self) -> None:
        """Test valid transitions from in_progress status."""
        transitions = VALID_STATUS_TRANSITIONS["in_progress"]
        assert "completed" in transitions
        assert "cancelled" in transitions
        assert len(transitions) == 2

    def test_completed_transitions(self) -> None:
        """Test valid transitions from completed status."""
        transitions = VALID_STATUS_TRANSITIONS["completed"]
        assert "closed" in transitions
        assert len(transitions) == 1

    def test_cancelled_is_terminal(self) -> None:
        """Test cancelled has no valid transitions."""
        transitions = VALID_STATUS_TRANSITIONS["cancelled"]
        assert len(transitions) == 0

    def test_closed_is_terminal(self) -> None:
        """Test closed has no valid transitions."""
        transitions = VALID_STATUS_TRANSITIONS["closed"]
        assert len(transitions) == 0


# =============================================================================
# JobStatusHistory Model Tests
# =============================================================================


class TestJobStatusHistoryModel:
    """Tests for JobStatusHistory model."""

    def test_tablename(self) -> None:
        """Test JobStatusHistory table name."""
        assert JobStatusHistory.__tablename__ == "job_status_history"

    def test_previous_status_enum_property_with_value(self) -> None:
        """Test previous_status_enum property returns correct enum."""
        history = JobStatusHistory()
        history.previous_status = "requested"
        assert history.previous_status_enum == JobStatus.REQUESTED

    def test_previous_status_enum_property_none(self) -> None:
        """Test previous_status_enum property returns None for initial."""
        history = JobStatusHistory()
        history.previous_status = None
        assert history.previous_status_enum is None

    def test_new_status_enum_property(self) -> None:
        """Test new_status_enum property returns correct enum."""
        history = JobStatusHistory()
        history.new_status = "approved"
        assert history.new_status_enum == JobStatus.APPROVED

    def test_to_dict(self) -> None:
        """Test to_dict method returns correct dictionary."""
        history = JobStatusHistory()
        history.previous_status = "requested"
        history.new_status = "approved"
        history.notes = "Customer approved the work"

        result = history.to_dict()

        assert result["previous_status"] == "requested"
        assert result["new_status"] == "approved"
        assert result["notes"] == "Customer approved the work"

    def test_repr(self) -> None:
        """Test __repr__ method."""
        history = JobStatusHistory()
        history.previous_status = "requested"
        history.new_status = "approved"

        repr_str = repr(history)

        assert "JobStatusHistory" in repr_str
        assert "requested" in repr_str
        assert "approved" in repr_str


# =============================================================================
# Staff Model Tests
# =============================================================================


class TestStaffModel:
    """Tests for Staff model."""

    def test_tablename(self) -> None:
        """Test Staff table name."""
        assert Staff.__tablename__ == "staff"

    def test_role_enum_property(self) -> None:
        """Test role_enum property returns correct enum."""
        staff = Staff()
        staff.role = "tech"
        assert staff.role_enum == StaffRole.TECH

    def test_skill_level_enum_property_with_value(self) -> None:
        """Test skill_level_enum property returns correct enum."""
        staff = Staff()
        staff.skill_level = "senior"
        assert staff.skill_level_enum == SkillLevel.SENIOR

    def test_skill_level_enum_property_none(self) -> None:
        """Test skill_level_enum property returns None when not set."""
        staff = Staff()
        staff.skill_level = None
        assert staff.skill_level_enum is None

    def test_to_dict(self) -> None:
        """Test to_dict method returns correct dictionary."""
        staff = Staff()
        staff.name = "Viktor Grin"
        staff.phone = "6125551001"
        staff.email = "viktor@grins-irrigation.com"
        staff.role = "admin"
        staff.skill_level = "lead"
        staff.hourly_rate = Decimal("75.00")
        staff.is_available = True
        staff.is_active = True

        result = staff.to_dict()

        assert result["name"] == "Viktor Grin"
        assert result["phone"] == "6125551001"
        assert result["email"] == "viktor@grins-irrigation.com"
        assert result["role"] == "admin"
        assert result["skill_level"] == "lead"
        assert result["hourly_rate"] == 75.00
        assert result["is_available"] is True
        assert result["is_active"] is True

    def test_repr(self) -> None:
        """Test __repr__ method."""
        staff = Staff()
        staff.name = "Test Staff"
        staff.role = "tech"

        repr_str = repr(staff)

        assert "Staff" in repr_str
        assert "Test Staff" in repr_str
        assert "tech" in repr_str
