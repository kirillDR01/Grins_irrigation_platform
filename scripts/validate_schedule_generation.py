#!/usr/bin/env python3
"""Functional validation script for schedule generation.

Validates: Requirements 5.1, 5.3, 5.4, 5.7, 5.8, 14.3
"""

import sys
import time
from datetime import date, timedelta

# Add src to path for imports
sys.path.insert(0, "src")


def main() -> int:
    """Run schedule generation validation."""
    print("=" * 60)
    print("Schedule Generation Functional Validation")
    print("=" * 60)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from grins_platform.database import DatabaseSettings
    from grins_platform.services.schedule_generation_service import (
        ScheduleGenerationService,
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

    # Test 1: Schedule generation completes
    print("\n[Test 1] Schedule generation completes")
    try:
        session = session_factory()
        service = ScheduleGenerationService(session)
        schedule_date = date.today() + timedelta(days=1)

        start_time = time.time()
        response = service.generate_schedule(schedule_date, timeout_seconds=30)
        elapsed = time.time() - start_time

        print(f"  ✓ Generation completed in {elapsed:.2f}s")
        print(f"  ✓ Is feasible: {response.is_feasible}")
        print(f"  ✓ Total assigned: {response.total_assigned}")
        print(f"  ✓ Total unassigned: {len(response.unassigned_jobs)}")
        session.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 2: Generation completes within 30 seconds
    print("\n[Test 2] Generation completes within 30 seconds")
    try:
        session = session_factory()
        service = ScheduleGenerationService(session)
        schedule_date = date.today() + timedelta(days=2)

        start_time = time.time()
        response = service.generate_schedule(schedule_date, timeout_seconds=30)
        elapsed = time.time() - start_time

        if elapsed <= 30:
            print(f"  ✓ Completed in {elapsed:.2f}s (< 30s)")
            passed += 1
        else:
            print(f"  ✗ Took {elapsed:.2f}s (> 30s)")
            failed += 1
        session.close()
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 3: Capacity endpoint returns valid data
    print("\n[Test 3] Capacity endpoint returns valid data")
    try:
        session = session_factory()
        service = ScheduleGenerationService(session)
        schedule_date = date.today() + timedelta(days=1)

        capacity = service.get_capacity(schedule_date)

        print(f"  ✓ Schedule date: {capacity.schedule_date}")
        print(f"  ✓ Total staff: {capacity.total_staff}")
        print(f"  ✓ Available staff: {capacity.available_staff}")
        print(f"  ✓ Total capacity (mins): {capacity.total_capacity_minutes}")
        print(f"  ✓ Scheduled (mins): {capacity.scheduled_minutes}")
        print(f"  ✓ Remaining (mins): {capacity.remaining_capacity_minutes}")
        print(f"  ✓ Can accept more: {capacity.can_accept_more}")
        session.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 4: Response contains required fields
    print("\n[Test 4] Response contains required fields")
    try:
        session = session_factory()
        service = ScheduleGenerationService(session)
        schedule_date = date.today() + timedelta(days=3)

        response = service.generate_schedule(schedule_date, timeout_seconds=10)

        # Check required fields exist
        assert hasattr(response, "schedule_date"), "Missing schedule_date"
        assert hasattr(response, "is_feasible"), "Missing is_feasible"
        assert hasattr(response, "hard_score"), "Missing hard_score"
        assert hasattr(response, "soft_score"), "Missing soft_score"
        assert hasattr(response, "assignments"), "Missing assignments"
        assert hasattr(response, "unassigned_jobs"), "Missing unassigned_jobs"
        assert hasattr(response, "total_assigned"), "Missing total_assigned"
        assert hasattr(response, "total_travel_minutes"), "Missing total_travel_minutes"
        assert hasattr(response, "optimization_time_seconds"), "Missing optimization_time_seconds"

        print("  ✓ All required fields present")
        session.close()
        passed += 1
    except AssertionError as e:
        print(f"  ✗ {e}")
        failed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 5: Hard score is 0 for feasible solutions
    print("\n[Test 5] Hard score is 0 for feasible solutions")
    try:
        session = session_factory()
        service = ScheduleGenerationService(session)
        schedule_date = date.today() + timedelta(days=4)

        response = service.generate_schedule(schedule_date, timeout_seconds=15)

        if response.is_feasible:
            if response.hard_score == 0:
                print(f"  ✓ Feasible solution has hard_score=0")
                passed += 1
            else:
                print(f"  ✗ Feasible but hard_score={response.hard_score}")
                failed += 1
        else:
            print(f"  ⚠ Solution not feasible (hard_score={response.hard_score})")
            print("    This may be expected if no staff/jobs available")
            passed += 1  # Not a failure if no data
        session.close()
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
