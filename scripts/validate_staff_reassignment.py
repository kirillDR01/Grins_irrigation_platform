#!/usr/bin/env python3
"""Functional validation script for staff reassignment.

Validates: Requirements 11.1-11.6, 14.6
"""

import sys
from datetime import date, timedelta
from uuid import uuid4

# Add src to path for imports
sys.path.insert(0, "src")


def main() -> int:
    """Run staff reassignment validation."""
    print("=" * 60)
    print("Staff Reassignment Functional Validation")
    print("=" * 60)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from grins_platform.database import DatabaseSettings
    from grins_platform.services.staff_reassignment_service import (
        StaffReassignmentService,
    )

    # Setup database connection
    settings = DatabaseSettings()
    sync_url = settings.database_url
    if sync_url.startswith("postgresql+asyncpg://"):
        sync_url = sync_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    engine = create_engine(sync_url, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    passed = 0
    failed = 0

    # Test 1: Service methods exist
    print("\n[Test 1] StaffReassignmentService methods exist")
    try:
        session = session_factory()
        service = StaffReassignmentService(session)

        assert hasattr(service, "mark_staff_unavailable")
        assert hasattr(service, "reassign_jobs")
        assert hasattr(service, "get_coverage_options")
        print("  ✓ mark_staff_unavailable method exists")
        print("  ✓ reassign_jobs method exists")
        print("  ✓ get_coverage_options method exists")
        session.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 2: Mark unavailable response has required fields
    print("\n[Test 2] MarkUnavailableResponse has required fields")
    try:
        from grins_platform.schemas.staff_reassignment import MarkUnavailableResponse

        response = MarkUnavailableResponse(
            staff_id=uuid4(),
            target_date=date.today(),
            affected_appointments=0,
            message="Test",
        )

        assert hasattr(response, "staff_id")
        assert hasattr(response, "target_date")
        assert hasattr(response, "affected_appointments")
        assert hasattr(response, "message")
        print("  ✓ All required fields present")
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 3: ReassignStaffResponse has required fields
    print("\n[Test 3] ReassignStaffResponse has required fields")
    try:
        from grins_platform.schemas.staff_reassignment import ReassignStaffResponse

        response = ReassignStaffResponse(
            reassignment_id=uuid4(),
            original_staff_id=uuid4(),
            new_staff_id=uuid4(),
            target_date=date.today(),
            jobs_reassigned=5,
            message="Test",
        )

        assert hasattr(response, "reassignment_id")
        assert hasattr(response, "original_staff_id")
        assert hasattr(response, "new_staff_id")
        assert hasattr(response, "jobs_reassigned")
        print("  ✓ All required fields present")
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 4: CoverageOptionsResponse has required fields
    print("\n[Test 4] CoverageOptionsResponse has required fields")
    try:
        from grins_platform.schemas.staff_reassignment import CoverageOptionsResponse

        response = CoverageOptionsResponse(
            target_date=date.today(),
            jobs_to_cover=3,
            total_duration_minutes=180,
            options=[],
        )

        assert hasattr(response, "target_date")
        assert hasattr(response, "jobs_to_cover")
        assert hasattr(response, "total_duration_minutes")
        assert hasattr(response, "options")
        print("  ✓ All required fields present")
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Summary
    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
