#!/usr/bin/env python3
"""Functional validation script for Wave 1 foundation tasks.

Validates:
- Task 4.5: Equipment assignment on staff
- Task 5.4: Staff starting location
- Task 6.3: Travel time calculation
"""

import sys
from decimal import Decimal

# Add src to path for imports
sys.path.insert(0, "src")

from grins_platform.utils.equipment import can_staff_handle_job
from grins_platform.services.travel_time_service import TravelTimeService


def validate_equipment_matching() -> bool:
    """Task 4.5: Validate equipment matching utility."""
    print("\n=== Task 4.5: Equipment Matching Validation ===")

    # Create mock staff and job objects
    class MockStaff:
        def __init__(self, equipment: list[str] | None):
            self.assigned_equipment = equipment

    class MockJob:
        def __init__(self, equipment: list[str] | None):
            self.equipment_required = equipment

    tests = [
        # (staff_equipment, job_equipment, expected_result, description)
        (["compressor", "pipe_puller"], ["compressor"], True, "Staff has required equipment"),
        (["compressor"], ["compressor", "pipe_puller"], False, "Staff missing equipment"),
        (["compressor", "pipe_puller"], None, True, "Job requires no equipment"),
        (["compressor", "pipe_puller"], [], True, "Job requires empty list"),
        (None, ["compressor"], False, "Staff has no equipment assigned"),
        ([], ["compressor"], False, "Staff has empty equipment list"),
        (None, None, True, "Both None - no requirements"),
        (["standard_tools"], ["standard_tools"], True, "Exact match"),
    ]

    all_passed = True
    for staff_eq, job_eq, expected, desc in tests:
        staff = MockStaff(staff_eq)
        job = MockJob(job_eq)
        result = can_staff_handle_job(staff, job)
        status = "✓" if result == expected else "✗"
        if result != expected:
            all_passed = False
        print(f"  {status} {desc}: {result} (expected {expected})")

    return all_passed


def validate_travel_time_service() -> bool:
    """Task 6.3: Validate travel time calculation."""
    print("\n=== Task 6.3: Travel Time Service Validation ===")

    service = TravelTimeService()

    # Test haversine fallback calculation
    # Eden Prairie to Plymouth (~10 miles)
    eden_prairie = (44.8547, -93.4708)
    plymouth = (45.0105, -93.4555)

    travel_time = service.calculate_fallback_travel_time(eden_prairie, plymouth)

    print(f"  Eden Prairie to Plymouth (haversine): {travel_time} minutes")

    # Should be roughly 15-35 minutes for ~10 miles at 30mph average
    if 10 <= travel_time <= 45:
        print("  ✓ Fallback travel time in reasonable range")
    else:
        print(f"  ✗ Fallback travel time out of range: {travel_time}")
        return False

    # Test same location (should be 0 or 1 - minimum travel time)
    same_loc_time = service.calculate_fallback_travel_time(eden_prairie, eden_prairie)
    print(f"  Same location travel time: {same_loc_time} minutes")
    if same_loc_time <= 1:
        print("  ✓ Same location returns minimal time")
    else:
        print(f"  ✗ Same location should be <=1, got {same_loc_time}")
        return False

    # Test longer distance: Eden Prairie to Rogers (~25 miles)
    rogers = (45.1889, -93.5530)
    long_travel = service.calculate_fallback_travel_time(eden_prairie, rogers)
    print(f"  Eden Prairie to Rogers (haversine): {long_travel} minutes")

    if long_travel > travel_time:
        print("  ✓ Longer distance = longer travel time")
    else:
        print("  ✗ Longer distance should have longer travel time")
        return False

    return True


def validate_staff_location_schema() -> bool:
    """Task 5.4: Validate staff starting location schema."""
    print("\n=== Task 5.4: Staff Starting Location Schema Validation ===")

    from grins_platform.schemas.staff import StaffCreate, StaffUpdate, StaffResponse
    from pydantic import ValidationError
    from datetime import datetime
    from uuid import uuid4

    # Test StaffCreate with location
    try:
        staff = StaffCreate(
            name="Test Tech",
            phone="6125551234",
            role="tech",
            default_start_address="123 Main St",
            default_start_city="Eden Prairie",
            default_start_lat=Decimal("44.8547"),
            default_start_lng=Decimal("-93.4708"),
            assigned_equipment=["compressor", "standard_tools"],
        )
        print(f"  ✓ StaffCreate with location: {staff.default_start_city}")
    except ValidationError as e:
        print(f"  ✗ StaffCreate failed: {e}")
        return False

    # Test StaffUpdate with partial location
    try:
        update = StaffUpdate(
            default_start_city="Plymouth",
            assigned_equipment=["pipe_puller"],
        )
        print(f"  ✓ StaffUpdate partial: city={update.default_start_city}")
    except ValidationError as e:
        print(f"  ✗ StaffUpdate failed: {e}")
        return False

    # Test StaffResponse with all fields
    try:
        response = StaffResponse(
            id=uuid4(),
            name="Test Tech",
            phone="6125551234",
            role="tech",
            is_available=True,
            is_active=True,
            default_start_address="123 Main St",
            default_start_city="Eden Prairie",
            default_start_lat=Decimal("44.8547"),
            default_start_lng=Decimal("-93.4708"),
            assigned_equipment=["compressor"],
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        print(f"  ✓ StaffResponse with location: lat={response.default_start_lat}")
    except ValidationError as e:
        print(f"  ✗ StaffResponse failed: {e}")
        return False

    # Test None values are allowed
    try:
        staff_no_loc = StaffCreate(
            name="No Location Tech",
            phone="6125559999",
            role="tech",
        )
        print(f"  ✓ StaffCreate without location: {staff_no_loc.default_start_city}")
    except ValidationError as e:
        print(f"  ✗ StaffCreate without location failed: {e}")
        return False

    return True


def main() -> int:
    """Run all Wave 1 validations."""
    print("=" * 60)
    print("Wave 1 Foundation Validation")
    print("=" * 60)

    results = []

    results.append(("Equipment Matching (4.5)", validate_equipment_matching()))
    results.append(("Staff Location Schema (5.4)", validate_staff_location_schema()))
    results.append(("Travel Time Service (6.3)", validate_travel_time_service()))

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✅ All Wave 1 validations PASSED!")
        return 0
    else:
        print("\n❌ Some validations FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
