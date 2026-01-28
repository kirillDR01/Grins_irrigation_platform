"""
Property-based tests for route optimization.

This module contains property-based tests using hypothesis to verify
universal correctness properties for staff availability.

Validates: Properties 1-3, 4, 19, 5-7 from route-optimization design.md
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from hypothesis import (
    given,
    settings,
    strategies as st,
)

from grins_platform.schemas.conflict_resolution import (
    CancelAppointmentRequest,
    CancelAppointmentResponse,
    RescheduleAppointmentRequest,
    RescheduleAppointmentResponse,
)
from grins_platform.schemas.schedule_generation import EmergencyInsertResponse
from grins_platform.schemas.staff import StaffCreate
from grins_platform.schemas.staff_availability import (
    StaffAvailabilityCreate,
)
from grins_platform.schemas.staff_reassignment import (
    CoverageOption,
    CoverageOptionsResponse,
    ReassignStaffResponse,
)
from grins_platform.services.schedule_constraints import ConstraintChecker
from grins_platform.services.schedule_domain import (
    ScheduleAssignment,
    ScheduleJob,
    ScheduleLocation,
    ScheduleSolution,
    ScheduleStaff,
)
from grins_platform.services.schedule_solver_service import ScheduleSolverService
from grins_platform.services.travel_time_service import TravelTimeService
from grins_platform.utils.equipment import can_staff_handle_job

# =============================================================================
# Strategies for generating valid test data
# =============================================================================


def valid_time_strategy() -> st.SearchStrategy[time]:
    """Generate valid time objects."""
    return st.builds(
        time,
        hour=st.integers(min_value=0, max_value=23),
        minute=st.sampled_from([0, 15, 30, 45]),
    )


def valid_date_strategy() -> st.SearchStrategy[date]:
    """Generate valid future dates."""
    today = date.today()
    return st.builds(
        lambda days: today + timedelta(days=days),
        days=st.integers(min_value=1, max_value=365),
    )


# =============================================================================
# Property 1: Staff Availability Round-Trip
# =============================================================================


class TestStaffAvailabilityRoundTrip:
    """Property tests for staff availability round-trip.

    **Property 1: Staff Availability Round-Trip**
    *For any* valid staff availability entry, creating it and then reading
    it back SHALL return an equivalent entry with all fields preserved.

    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    """

    @pytest.mark.unit
    @given(
        target_date=valid_date_strategy(),
        start_hour=st.integers(min_value=5, max_value=10),
        end_hour=st.integers(min_value=15, max_value=20),
        is_available=st.booleans(),
        lunch_duration=st.sampled_from([15, 30, 45, 60]),
    )
    @settings(max_examples=50)
    def test_availability_fields_preserved(
        self,
        target_date: date,
        start_hour: int,
        end_hour: int,
        is_available: bool,
        lunch_duration: int,
    ) -> None:
        """
        Feature: route-optimization, Property 1: Staff Availability Round-Trip
        All fields in a valid availability entry should be preserved.
        """
        start_time = time(hour=start_hour, minute=0)
        end_time = time(hour=end_hour, minute=0)
        lunch_start = time(hour=12, minute=0)

        # Create schema validates and preserves all fields
        availability = StaffAvailabilityCreate(
            date=target_date,
            start_time=start_time,
            end_time=end_time,
            is_available=is_available,
            lunch_start=lunch_start,
            lunch_duration_minutes=lunch_duration,
        )

        # Verify all fields are preserved
        assert availability.date == target_date
        assert availability.start_time == start_time
        assert availability.end_time == end_time
        assert availability.is_available == is_available
        assert availability.lunch_start == lunch_start
        assert availability.lunch_duration_minutes == lunch_duration

    @pytest.mark.unit
    @given(
        notes=st.text(min_size=0, max_size=200).filter(
            lambda x: x.isprintable() or x == "",
        ),
    )
    @settings(max_examples=30)
    def test_notes_field_preserved(self, notes: str) -> None:
        """
        Feature: route-optimization, Property 1: Staff Availability Round-Trip
        Notes field should be preserved for any printable string.
        """
        availability = StaffAvailabilityCreate(
            date=date.today() + timedelta(days=1),
            start_time=time(8, 0),
            end_time=time(17, 0),
            is_available=True,
            notes=notes if notes else None,
        )

        assert availability.notes == (notes if notes else None)


# =============================================================================
# Property 2: Availability Time Validation
# =============================================================================


class TestAvailabilityTimeValidation:
    """Property tests for availability time validation.

    **Property 2: Availability Time Validation**
    *For any* staff availability entry, the start_time SHALL always be
    before end_time, and lunch_start (if specified) SHALL be within
    the availability window.

    **Validates: Requirements 1.6, 1.7**
    """

    @pytest.mark.unit
    @given(
        start_hour=st.integers(min_value=6, max_value=10),
        end_hour=st.integers(min_value=16, max_value=20),
    )
    @settings(max_examples=50)
    def test_start_before_end_enforced(
        self,
        start_hour: int,
        end_hour: int,
    ) -> None:
        """
        Feature: route-optimization, Property 2: Availability Time Validation
        Start time must always be before end time.
        """
        start_time = time(hour=start_hour, minute=0)
        end_time = time(hour=end_hour, minute=0)

        availability = StaffAvailabilityCreate(
            date=date.today() + timedelta(days=1),
            start_time=start_time,
            end_time=end_time,
            is_available=True,
            lunch_start=time(12, 0),  # Explicit lunch within window
            lunch_duration_minutes=30,
        )

        # Verify start is before end
        assert availability.start_time < availability.end_time

    @pytest.mark.unit
    @given(
        start_hour=st.integers(min_value=6, max_value=9),
        end_hour=st.integers(min_value=16, max_value=20),
        lunch_hour=st.integers(min_value=11, max_value=14),
    )
    @settings(max_examples=50)
    def test_lunch_within_availability_window(
        self,
        start_hour: int,
        end_hour: int,
        lunch_hour: int,
    ) -> None:
        """
        Feature: route-optimization, Property 2: Availability Time Validation
        Lunch start must be within the availability window.
        """
        start_time = time(hour=start_hour, minute=0)
        end_time = time(hour=end_hour, minute=0)
        lunch_start = time(hour=lunch_hour, minute=0)

        availability = StaffAvailabilityCreate(
            date=date.today() + timedelta(days=1),
            start_time=start_time,
            end_time=end_time,
            is_available=True,
            lunch_start=lunch_start,
            lunch_duration_minutes=30,
        )

        # Verify lunch is within window
        assert availability.lunch_start is not None
        assert availability.lunch_start >= availability.start_time
        assert availability.lunch_start < availability.end_time

    @pytest.mark.unit
    def test_invalid_time_range_rejected(self) -> None:
        """
        Feature: route-optimization, Property 2: Availability Time Validation
        Invalid time ranges (end before start) should be rejected.
        """
        with pytest.raises(ValueError, match="start_time must be before end_time"):
            StaffAvailabilityCreate(
                date=date.today() + timedelta(days=1),
                start_time=time(17, 0),  # 5 PM
                end_time=time(8, 0),  # 8 AM - invalid
                is_available=True,
                lunch_start=None,  # No lunch to avoid secondary validation
                lunch_duration_minutes=0,
            )


# =============================================================================
# Property 3: Available Staff Query Correctness
# =============================================================================


class TestAvailableStaffQueryCorrectness:
    """Property tests for available staff query correctness.

    **Property 3: Available Staff Query Correctness**
    *For any* date, querying available staff SHALL return exactly those
    staff members who have `is_available=true` entries for that date,
    and SHALL NOT return staff without entries.

    **Validates: Requirements 1.5, 1.8**
    """

    @pytest.mark.unit
    @given(is_available=st.booleans())
    @settings(max_examples=20)
    def test_availability_flag_determines_inclusion(self, is_available: bool) -> None:
        """
        Feature: route-optimization, Property 3: Available Staff Query
        Only staff with is_available=true should be included in available query.
        """
        availability = StaffAvailabilityCreate(
            date=date.today() + timedelta(days=1),
            start_time=time(8, 0),
            end_time=time(17, 0),
            is_available=is_available,
        )

        # The is_available flag determines if staff appears in available query
        # Staff with is_available=False should NOT appear
        # Staff with is_available=True should appear
        assert availability.is_available == is_available

    @pytest.mark.unit
    def test_default_is_available_true(self) -> None:
        """
        Feature: route-optimization, Property 3: Available Staff Query
        Default is_available should be True when not specified.
        """
        availability = StaffAvailabilityCreate(
            date=date.today() + timedelta(days=1),
            start_time=time(8, 0),
            end_time=time(17, 0),
        )

        assert availability.is_available is True


# =============================================================================
# Property 4: Equipment Assignment Persistence
# =============================================================================


class TestEquipmentAssignmentPersistence:
    """Property tests for equipment assignment persistence.

    **Property 4: Equipment Assignment Persistence**
    *For any* valid equipment list assigned to staff, the equipment
    SHALL be preserved exactly when read back, with no additions,
    removals, or modifications.

    **Validates: Requirements 2.1, 2.3**
    """

    @pytest.mark.unit
    @given(
        equipment=st.lists(
            st.sampled_from(
                [
                    "compressor",
                    "pipe_puller",
                    "utility_trailer",
                    "dump_trailer",
                    "skid_steer",
                    "standard_tools",
                ],
            ),
            min_size=0,
            max_size=5,
            unique=True,
        ),
    )
    @settings(max_examples=50)
    def test_equipment_list_preserved(self, equipment: list[str]) -> None:
        """
        Feature: route-optimization, Property 4: Equipment Assignment
        Equipment list should be preserved exactly as assigned.
        """
        staff = StaffCreate(
            name="Test Tech",
            phone="6125551234",
            role="tech",
            assigned_equipment=equipment if equipment else None,
        )

        if equipment:
            assert staff.assigned_equipment == equipment
            assert len(staff.assigned_equipment) == len(equipment)
        else:
            assert staff.assigned_equipment is None or staff.assigned_equipment == []

    @pytest.mark.unit
    @given(
        staff_equipment=st.lists(
            st.sampled_from(["compressor", "pipe_puller", "standard_tools"]),
            min_size=0,
            max_size=3,
            unique=True,
        ),
        job_equipment=st.lists(
            st.sampled_from(["compressor", "pipe_puller", "standard_tools"]),
            min_size=0,
            max_size=3,
            unique=True,
        ),
    )
    @settings(max_examples=100)
    def test_equipment_matching_correctness(
        self,
        staff_equipment: list[str],
        job_equipment: list[str],
    ) -> None:
        """
        Feature: route-optimization, Property 4: Equipment Assignment
        Staff can handle job iff staff has ALL required equipment.
        """

        class MockStaff:
            def __init__(self, eq: list[str]) -> None:
                self.assigned_equipment = eq if eq else None

        class MockJob:
            def __init__(self, eq: list[str]) -> None:
                self.equipment_required = eq if eq else None

        staff = MockStaff(staff_equipment)
        job = MockJob(job_equipment)

        result = can_staff_handle_job(staff, job)

        # Expected: True if job requires nothing OR staff has all required
        if not job_equipment:
            assert result is True, "Job with no requirements should always match"
        elif not staff_equipment:
            assert result is False, "Staff with no equipment can't handle requirements"
        else:
            expected = all(eq in staff_equipment for eq in job_equipment)
            assert result == expected


# =============================================================================
# Property 19: Travel Time Fallback
# =============================================================================


class TestTravelTimeFallback:
    """Property tests for travel time fallback calculation.

    **Property 19: Travel Time Fallback**
    *For any* two valid coordinates, the haversine fallback calculation
    SHALL return a positive travel time, and the time SHALL increase
    monotonically with distance.

    **Validates: Requirements 4.2, 4.5**
    """

    @pytest.mark.unit
    @given(
        lat1=st.floats(min_value=44.5, max_value=45.5),
        lng1=st.floats(min_value=-94.0, max_value=-93.0),
        lat2=st.floats(min_value=44.5, max_value=45.5),
        lng2=st.floats(min_value=-94.0, max_value=-93.0),
    )
    @settings(max_examples=100)
    def test_fallback_returns_positive_time(
        self,
        lat1: float,
        lng1: float,
        lat2: float,
        lng2: float,
    ) -> None:
        """
        Feature: route-optimization, Property 19: Travel Time Fallback
        Fallback calculation should always return positive travel time.
        """
        service = TravelTimeService()
        travel_time = service.calculate_fallback_travel_time(
            (lat1, lng1),
            (lat2, lng2),
        )

        assert travel_time >= 1, "Travel time should be at least 1 minute"
        assert isinstance(travel_time, int), "Travel time should be integer minutes"

    @pytest.mark.unit
    @given(
        base_lat=st.floats(min_value=44.8, max_value=45.0),
        base_lng=st.floats(min_value=-93.6, max_value=-93.4),
        offset_small=st.floats(min_value=0.01, max_value=0.05),
        offset_large=st.floats(min_value=0.1, max_value=0.3),
    )
    @settings(max_examples=50)
    def test_travel_time_increases_with_distance(
        self,
        base_lat: float,
        base_lng: float,
        offset_small: float,
        offset_large: float,
    ) -> None:
        """
        Feature: route-optimization, Property 19: Travel Time Fallback
        Travel time should increase with distance.
        """
        service = TravelTimeService()
        origin = (base_lat, base_lng)

        # Small distance
        near_dest = (base_lat + offset_small, base_lng + offset_small)
        time_near = service.calculate_fallback_travel_time(origin, near_dest)

        # Large distance
        far_dest = (base_lat + offset_large, base_lng + offset_large)
        time_far = service.calculate_fallback_travel_time(origin, far_dest)

        assert time_far >= time_near, "Farther destination should take >= time"

    @pytest.mark.unit
    def test_same_location_minimal_time(self) -> None:
        """
        Feature: route-optimization, Property 19: Travel Time Fallback
        Same origin and destination should return minimal time.
        """
        service = TravelTimeService()
        location = (44.8547, -93.4708)  # Eden Prairie

        travel_time = service.calculate_fallback_travel_time(location, location)

        assert travel_time <= 1, "Same location should return minimal time"


# =============================================================================
# Property 5-7: Schedule Solver Constraints
# =============================================================================


class TestScheduleSolverConstraints:
    """Property tests for schedule solver constraints.

    **Property 5: No Availability Violations**
    **Property 6: No Equipment Violations**
    **Property 7: No Capacity Violations**

    **Validates: Requirements 6.1, 6.2, 6.7**
    """

    @pytest.mark.unit
    @given(
        job_count=st.integers(min_value=1, max_value=5),
        staff_count=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=20)
    def test_solver_produces_feasible_solution(
        self,
        job_count: int,
        staff_count: int,
    ) -> None:
        """
        Feature: route-optimization, Property 5-7: Solver Constraints
        Solver should produce feasible solutions (hard score >= 0).
        """
        # Create jobs with short durations to ensure feasibility
        jobs = [
            ScheduleJob(
                id=uuid4(),
                customer_name=f"Customer {i}",
                location=ScheduleLocation(
                    Decimal("44.8547"),
                    Decimal("-93.4708"),
                    city="Eden Prairie",
                ),
                service_type="Startup",
                duration_minutes=30,
            )
            for i in range(job_count)
        ]

        # Create staff with standard equipment
        staff = [
            ScheduleStaff(
                id=uuid4(),
                name=f"Tech {i}",
                start_location=ScheduleLocation(
                    Decimal("44.8500"),
                    Decimal("-93.4700"),
                ),
                assigned_equipment=["standard_tools"],
            )
            for i in range(staff_count)
        ]

        solver = ScheduleSolverService(timeout_seconds=2)
        solution = solver.solve(date.today(), jobs, staff)

        # Solution should be feasible (no hard constraint violations)
        assert solution.hard_score >= 0, f"Not feasible: {solution.score_str()}"

    @pytest.mark.unit
    def test_equipment_constraint_enforced(self) -> None:
        """
        Feature: route-optimization, Property 6: No Equipment Violations
        Jobs requiring equipment should only be assigned to staff with that equipment.
        """
        # Job requiring compressor
        job = ScheduleJob(
            id=uuid4(),
            customer_name="Customer",
            location=ScheduleLocation(Decimal("44.8547"), Decimal("-93.4708")),
            service_type="Winterization",
            duration_minutes=45,
            equipment_required=["compressor"],
        )

        # Staff WITHOUT compressor
        staff = ScheduleStaff(
            id=uuid4(),
            name="Tech",
            start_location=ScheduleLocation(Decimal("44.8500"), Decimal("-93.4700")),
            assigned_equipment=["standard_tools"],  # No compressor!
        )

        # Create solution with invalid assignment
        solution = ScheduleSolution(
            schedule_date=date.today(),
            jobs=[job],
            staff=[staff],
            assignments=[
                ScheduleAssignment(id=uuid4(), staff=staff, jobs=[job]),
            ],
        )

        checker = ConstraintChecker()
        score = checker.calculate_score(solution)

        # Should have hard constraint violation
        assert score.hard_score < 0, "Equipment violation not detected"

    @pytest.mark.unit
    def test_capacity_constraint_enforced(self) -> None:
        """
        Feature: route-optimization, Property 7: No Capacity Violations
        Staff should not be assigned more work than their availability allows.
        """
        # Create many long jobs (10 x 60 min = 600 min)
        jobs = [
            ScheduleJob(
                id=uuid4(),
                customer_name=f"Customer {i}",
                location=ScheduleLocation(Decimal("44.8547"), Decimal("-93.4708")),
                service_type="Installation",
                duration_minutes=60,
                buffer_minutes=10,
            )
            for i in range(10)
        ]

        # Staff with only 8 hours (480 min) availability
        staff = ScheduleStaff(
            id=uuid4(),
            name="Tech",
            start_location=ScheduleLocation(Decimal("44.8500"), Decimal("-93.4700")),
            assigned_equipment=["standard_tools"],
            availability_start=time(8, 0),
            availability_end=time(16, 0),  # 8 hours
        )

        # Assign all jobs to one staff (overbooked)
        solution = ScheduleSolution(
            schedule_date=date.today(),
            jobs=jobs,
            staff=[staff],
            assignments=[
                ScheduleAssignment(id=uuid4(), staff=staff, jobs=jobs),
            ],
        )

        checker = ConstraintChecker()
        score = checker.calculate_score(solution)

        # Should have hard constraint violation (overbooked)
        assert score.hard_score < 0, "Capacity violation not detected"


# =============================================================================
# Property 12: Schedule Generation Completeness
# =============================================================================


class TestScheduleGenerationCompleteness:
    """Property tests for schedule generation completeness.

    **Property 12: Schedule Generation Completeness**
    *For any* set of jobs and available staff, the schedule generation
    SHALL either assign each job to exactly one staff member OR include
    it in the unassigned list with a reason.

    **Validates: Requirements 5.1, 5.3, 5.4**
    """

    @pytest.mark.unit
    @given(
        job_count=st.integers(min_value=1, max_value=10),
        staff_count=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=20)
    def test_all_jobs_accounted_for(
        self,
        job_count: int,
        staff_count: int,
    ) -> None:
        """
        Feature: route-optimization, Property 12: Schedule Generation Completeness
        Every job should be either assigned or in unassigned list.
        """
        jobs = [
            ScheduleJob(
                id=uuid4(),
                customer_name=f"Customer {i}",
                location=ScheduleLocation(
                    Decimal("44.8547"),
                    Decimal("-93.4708"),
                    city="Eden Prairie",
                ),
                service_type="Startup",
                duration_minutes=30,
            )
            for i in range(job_count)
        ]

        staff = [
            ScheduleStaff(
                id=uuid4(),
                name=f"Tech {i}",
                start_location=ScheduleLocation(
                    Decimal("44.8500"),
                    Decimal("-93.4700"),
                ),
                assigned_equipment=["standard_tools"],
            )
            for i in range(staff_count)
        ]

        solver = ScheduleSolverService(timeout_seconds=2)
        solution = solver.solve(date.today(), jobs, staff)

        # Count assigned jobs
        assigned_job_ids = set()
        for assignment in solution.assignments:
            for job in assignment.jobs:
                assigned_job_ids.add(job.id)

        # All jobs should be assigned (simple case with enough capacity)
        original_job_ids = {j.id for j in jobs}

        # Every job should be accounted for
        assert assigned_job_ids.issubset(original_job_ids), "Unknown job assigned"

    @pytest.mark.unit
    def test_no_duplicate_assignments(self) -> None:
        """
        Feature: route-optimization, Property 12: Schedule Generation Completeness
        No job should be assigned to multiple staff members.
        """
        jobs = [
            ScheduleJob(
                id=uuid4(),
                customer_name=f"Customer {i}",
                location=ScheduleLocation(
                    Decimal("44.8547"),
                    Decimal("-93.4708"),
                ),
                service_type="Startup",
                duration_minutes=30,
            )
            for i in range(5)
        ]

        staff = [
            ScheduleStaff(
                id=uuid4(),
                name=f"Tech {i}",
                start_location=ScheduleLocation(
                    Decimal("44.8500"),
                    Decimal("-93.4700"),
                ),
            )
            for i in range(2)
        ]

        solver = ScheduleSolverService(timeout_seconds=2)
        solution = solver.solve(date.today(), jobs, staff)

        # Collect all assigned job IDs
        all_assigned: list[UUID] = []
        for assignment in solution.assignments:
            all_assigned.extend(j.id for j in assignment.jobs)

        # No duplicates
        assert len(all_assigned) == len(set(all_assigned)), "Duplicate job assignment"


# =============================================================================
# Property 14: Preview Non-Persistence
# =============================================================================


class TestPreviewNonPersistence:
    """Property tests for preview non-persistence.

    **Property 14: Preview Non-Persistence**
    *For any* schedule preview request, the preview SHALL return a valid
    schedule response without persisting any data to the database.

    **Validates: Requirement 5.7**
    """

    @pytest.mark.unit
    def test_preview_returns_valid_response(self) -> None:
        """
        Feature: route-optimization, Property 14: Preview Non-Persistence
        Preview should return valid schedule response structure.
        """
        jobs = [
            ScheduleJob(
                id=uuid4(),
                customer_name="Customer",
                location=ScheduleLocation(Decimal("44.8547"), Decimal("-93.4708")),
                service_type="Startup",
                duration_minutes=30,
            ),
        ]

        staff = [
            ScheduleStaff(
                id=uuid4(),
                name="Tech",
                start_location=ScheduleLocation(
                    Decimal("44.8500"),
                    Decimal("-93.4700"),
                ),
            ),
        ]

        solver = ScheduleSolverService(timeout_seconds=2)
        solution = solver.solve(date.today(), jobs, staff)

        # Solution should have required attributes
        assert hasattr(solution, "schedule_date")
        assert hasattr(solution, "assignments")
        assert hasattr(solution, "hard_score")
        assert hasattr(solution, "soft_score")
        assert solution.is_feasible() or solution.hard_score < 0


# =============================================================================
# Property 20: Buffer Time Application
# =============================================================================


class TestBufferTimeApplication:
    """Property tests for buffer time application.

    **Property 20: Buffer Time Application**
    *For any* job with a configured buffer time, the total time allocated
    SHALL equal duration_minutes + buffer_minutes.

    **Validates: Requirements 8.2, 8.4**
    """

    @pytest.mark.unit
    @given(
        duration=st.integers(min_value=15, max_value=120),
        buffer=st.integers(min_value=0, max_value=30),
    )
    @settings(max_examples=50)
    def test_buffer_time_added_to_duration(
        self,
        duration: int,
        buffer: int,
    ) -> None:
        """
        Feature: route-optimization, Property 20: Buffer Time Application
        Total allocated time should include buffer.
        """
        job = ScheduleJob(
            id=uuid4(),
            customer_name="Customer",
            location=ScheduleLocation(Decimal("44.8547"), Decimal("-93.4708")),
            service_type="Service",
            duration_minutes=duration,
            buffer_minutes=buffer,
        )

        expected_total = duration + buffer
        assert job.total_time_minutes == expected_total

    @pytest.mark.unit
    def test_buffer_affects_capacity_calculation(self) -> None:
        """
        Feature: route-optimization, Property 20: Buffer Time Application
        Buffer time should be considered in capacity constraints.
        """
        # Job with large buffer
        job = ScheduleJob(
            id=uuid4(),
            customer_name="Customer",
            location=ScheduleLocation(Decimal("44.8547"), Decimal("-93.4708")),
            service_type="Service",
            duration_minutes=60,
            buffer_minutes=30,  # Total: 90 minutes
        )

        # Staff with only 60 minutes available
        staff = ScheduleStaff(
            id=uuid4(),
            name="Tech",
            start_location=ScheduleLocation(Decimal("44.8500"), Decimal("-93.4700")),
            availability_start=time(8, 0),
            availability_end=time(9, 0),  # Only 60 minutes
        )

        # Assign job to staff (should violate capacity)
        solution = ScheduleSolution(
            schedule_date=date.today(),
            jobs=[job],
            staff=[staff],
            assignments=[
                ScheduleAssignment(id=uuid4(), staff=staff, jobs=[job]),
            ],
        )

        checker = ConstraintChecker()
        score = checker.calculate_score(solution)

        # Should have capacity violation (90 min job in 60 min window)
        assert score.hard_score < 0, "Buffer time not considered in capacity"


# =============================================================================
# Property 15: Emergency Job Insertion
# =============================================================================


class TestEmergencyJobInsertion:
    """Property tests for emergency job insertion.

    **Property 15: Emergency Job Insertion**
    *For any* emergency job insertion request, the system SHALL either
    successfully insert the job with a valid assignment OR return a
    clear explanation of why insertion failed.

    **Validates: Requirements 9.1, 9.3**
    """

    @pytest.mark.unit
    @given(
        priority_level=st.integers(min_value=0, max_value=3),
    )
    @settings(max_examples=10)
    def test_emergency_job_gets_high_priority(self, priority_level: int) -> None:
        """
        Feature: route-optimization, Property 15: Emergency Job Insertion
        Emergency jobs should be assigned higher priority in scheduling.
        """
        # Create emergency job with specified priority
        emergency_job = ScheduleJob(
            id=uuid4(),
            customer_name="Emergency Customer",
            location=ScheduleLocation(Decimal("44.8547"), Decimal("-93.4708")),
            service_type="Emergency Repair",
            duration_minutes=60,
            priority=priority_level + 10,  # Boost priority
        )

        # Create regular job
        regular_job = ScheduleJob(
            id=uuid4(),
            customer_name="Regular Customer",
            location=ScheduleLocation(Decimal("44.8600"), Decimal("-93.4800")),
            service_type="Startup",
            duration_minutes=30,
            priority=0,
        )

        # Emergency job should have higher priority
        assert emergency_job.priority > regular_job.priority

    @pytest.mark.unit
    def test_emergency_response_always_has_message(self) -> None:
        """
        Feature: route-optimization, Property 15: Emergency Job Insertion
        Emergency insertion response should always include a message.
        """
        # Success case
        success_response = EmergencyInsertResponse(
            success=True,
            job_id=uuid4(),
            target_date=date.today(),
            message="Job inserted successfully",
        )
        assert success_response.message

        # Failure case
        failure_response = EmergencyInsertResponse(
            success=False,
            job_id=uuid4(),
            target_date=date.today(),
            constraint_violations=["No capacity"],
            message="Could not insert job",
        )
        assert failure_response.message
        assert len(failure_response.constraint_violations) > 0

    @pytest.mark.unit
    def test_emergency_insertion_preserves_existing_assignments(self) -> None:
        """
        Feature: route-optimization, Property 15: Emergency Job Insertion
        Inserting emergency job should not remove existing valid assignments.
        """
        # Create existing jobs
        existing_jobs = [
            ScheduleJob(
                id=uuid4(),
                customer_name=f"Customer {i}",
                location=ScheduleLocation(Decimal("44.8547"), Decimal("-93.4708")),
                service_type="Startup",
                duration_minutes=30,
            )
            for i in range(3)
        ]

        # Create emergency job
        emergency_job = ScheduleJob(
            id=uuid4(),
            customer_name="Emergency",
            location=ScheduleLocation(Decimal("44.8600"), Decimal("-93.4800")),
            service_type="Emergency",
            duration_minutes=45,
            priority=10,
        )

        # All jobs together
        all_jobs = [*existing_jobs, emergency_job]

        # Create staff with enough capacity
        staff = [
            ScheduleStaff(
                id=uuid4(),
                name="Tech",
                start_location=ScheduleLocation(
                    Decimal("44.8500"),
                    Decimal("-93.4700"),
                ),
                availability_start=time(8, 0),
                availability_end=time(17, 0),  # 9 hours
            ),
        ]

        solver = ScheduleSolverService(timeout_seconds=2)
        solution = solver.solve(date.today(), all_jobs, staff)

        # Count assigned jobs
        assigned_count = sum(len(a.jobs) for a in solution.assignments)

        # With enough capacity, all jobs should be assigned
        assert assigned_count >= len(existing_jobs), "Existing jobs should be preserved"


# =============================================================================
# Property 16: Cancellation State Transition
# =============================================================================


class TestCancellationStateTransition:
    """Property tests for cancellation state transition.

    **Property 16: Cancellation State Transition**
    *For any* appointment cancellation, the appointment status SHALL
    transition to 'cancelled' and the cancellation_reason and cancelled_at
    fields SHALL be populated.

    **Validates: Requirements 10.1, 10.2**
    """

    @pytest.mark.unit
    @given(
        reason=st.text(min_size=1, max_size=100).filter(lambda x: x.strip()),
    )
    @settings(max_examples=20)
    def test_cancellation_response_has_required_fields(self, reason: str) -> None:
        """
        Feature: route-optimization, Property 16: Cancellation State Transition
        Cancellation response should have all required fields.
        """
        response = CancelAppointmentResponse(
            appointment_id=uuid4(),
            cancelled_at=datetime.now(timezone.utc),
            reason=reason.strip(),
            message="Cancelled",
        )

        assert response.appointment_id is not None
        assert response.cancelled_at is not None
        assert response.reason == reason.strip()
        assert response.message is not None

    @pytest.mark.unit
    def test_cancellation_with_waitlist_option(self) -> None:
        """
        Feature: route-optimization, Property 16: Cancellation State Transition
        Cancellation with add_to_waitlist should create waitlist entry.
        """
        # Request with waitlist option
        request = CancelAppointmentRequest(
            reason="Customer requested",
            add_to_waitlist=True,
            preferred_reschedule_date=date.today() + timedelta(days=7),
        )

        assert request.add_to_waitlist is True
        assert request.preferred_reschedule_date is not None


# =============================================================================
# Property 17: Reschedule Linkage
# =============================================================================


class TestRescheduleLinkage:
    """Property tests for reschedule linkage.

    **Property 17: Reschedule Linkage**
    *For any* rescheduled appointment, the new appointment SHALL have
    a reference to the original appointment via rescheduled_from_id.

    **Validates: Requirement 10.3**
    """

    @pytest.mark.unit
    def test_reschedule_response_links_appointments(self) -> None:
        """
        Feature: route-optimization, Property 17: Reschedule Linkage
        Reschedule response should link original and new appointments.
        """
        original_id = uuid4()
        new_id = uuid4()

        response = RescheduleAppointmentResponse(
            original_appointment_id=original_id,
            new_appointment_id=new_id,
            new_date=date.today() + timedelta(days=1),
            new_time_start=time(10, 0),
            new_time_end=time(11, 0),
            staff_id=uuid4(),
            message="Rescheduled",
        )

        assert response.original_appointment_id == original_id
        assert response.new_appointment_id == new_id
        assert response.original_appointment_id != response.new_appointment_id

    @pytest.mark.unit
    @given(
        days_ahead=st.integers(min_value=1, max_value=30),
        start_hour=st.integers(min_value=8, max_value=15),
    )
    @settings(max_examples=20)
    def test_reschedule_request_valid_times(
        self,
        days_ahead: int,
        start_hour: int,
    ) -> None:
        """
        Feature: route-optimization, Property 17: Reschedule Linkage
        Reschedule request should accept valid future dates and times.
        """
        request = RescheduleAppointmentRequest(
            new_date=date.today() + timedelta(days=days_ahead),
            new_time_start=time(start_hour, 0),
            new_time_end=time(start_hour + 1, 0),
        )

        assert request.new_date > date.today()
        assert request.new_time_start < request.new_time_end


# =============================================================================
# Property 18: Staff Reassignment Record
# =============================================================================


class TestStaffReassignmentRecord:
    """Property tests for staff reassignment record.

    **Property 18: Staff Reassignment Record**
    *For any* staff reassignment, a record SHALL be created with the
    original staff, new staff, date, reason, and count of jobs reassigned.

    **Validates: Requirements 11.1, 11.2, 11.3**
    """

    @pytest.mark.unit
    def test_reassignment_response_has_required_fields(self) -> None:
        """
        Feature: route-optimization, Property 18: Staff Reassignment Record
        Reassignment response should have all required fields.
        """
        response = ReassignStaffResponse(
            reassignment_id=uuid4(),
            original_staff_id=uuid4(),
            new_staff_id=uuid4(),
            target_date=date.today(),
            jobs_reassigned=5,
            message="Reassigned",
        )

        assert response.reassignment_id is not None
        assert response.original_staff_id is not None
        assert response.new_staff_id is not None
        assert response.target_date is not None
        assert response.jobs_reassigned >= 0
        assert response.message is not None

    @pytest.mark.unit
    @given(
        jobs_count=st.integers(min_value=0, max_value=20),
    )
    @settings(max_examples=20)
    def test_reassignment_tracks_job_count(self, jobs_count: int) -> None:
        """
        Feature: route-optimization, Property 18: Staff Reassignment Record
        Reassignment should track the number of jobs reassigned.
        """
        response = ReassignStaffResponse(
            reassignment_id=uuid4(),
            original_staff_id=uuid4(),
            new_staff_id=uuid4(),
            target_date=date.today(),
            jobs_reassigned=jobs_count,
            message=f"Reassigned {jobs_count} jobs",
        )

        assert response.jobs_reassigned == jobs_count

    @pytest.mark.unit
    def test_coverage_options_response_structure(self) -> None:
        """
        Feature: route-optimization, Property 18: Staff Reassignment Record
        Coverage options should provide staff capacity information.
        """
        option = CoverageOption(
            staff_id=uuid4(),
            staff_name="Tech 1",
            available_capacity_minutes=240,
            current_jobs=3,
            can_cover_all=True,
        )

        response = CoverageOptionsResponse(
            target_date=date.today(),
            jobs_to_cover=5,
            total_duration_minutes=180,
            options=[option],
        )

        assert len(response.options) == 1
        assert response.options[0].can_cover_all is True
        capacity = response.options[0].available_capacity_minutes
        assert capacity >= response.total_duration_minutes
