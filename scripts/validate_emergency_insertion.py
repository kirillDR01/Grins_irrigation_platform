#!/usr/bin/env python3
"""Functional validation script for emergency job insertion.

Validates: Requirements 9.1, 9.3, 14.4
"""

import sys
import time
from datetime import date, timedelta
from uuid import uuid4

# Add src to path for imports
sys.path.insert(0, "src")


def main() -> int:
    """Run emergency insertion validation."""
    print("=" * 60)
    print("Emergency Job Insertion Functional Validation")
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

    # Test 1: Emergency insertion with valid job
    print("\n[Test 1] Emergency insertion service method exists")
    try:
        session = session_factory()
        service = ScheduleGenerationService(session)

        # Check method exists
        assert hasattr(service, "insert_emergency_job")
        assert hasattr(service, "reoptimize_schedule")
        print("  ✓ insert_emergency_job method exists")
        print("  ✓ reoptimize_schedule method exists")
        session.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 2: Emergency insertion with non-existent job
    print("\n[Test 2] Emergency insertion with non-existent job")
    try:
        session = session_factory()
        service = ScheduleGenerationService(session)
        target_date = date.today() + timedelta(days=1)

        response = service.insert_emergency_job(
            job_id=uuid4(),  # Non-existent job
            target_date=target_date,
            priority_level=2,
        )

        assert response.success is False
        assert "not found" in response.message.lower()
        print(f"  ✓ Returns success=False for non-existent job")
        print(f"  ✓ Message: {response.message}")
        session.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 3: Re-optimization completes within 15 seconds
    print("\n[Test 3] Re-optimization completes within 15 seconds")
    try:
        session = session_factory()
        service = ScheduleGenerationService(session)
        target_date = date.today() + timedelta(days=2)

        start_time = time.time()
        response = service.reoptimize_schedule(target_date, timeout_seconds=15)
        elapsed = time.time() - start_time

        if elapsed <= 15:
            print(f"  ✓ Re-optimization completed in {elapsed:.2f}s (< 15s)")
            passed += 1
        else:
            print(f"  ✗ Took {elapsed:.2f}s (> 15s)")
            failed += 1
        session.close()
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 4: EmergencyInsertResponse has required fields
    print("\n[Test 4] EmergencyInsertResponse has required fields")
    try:
        session = session_factory()
        service = ScheduleGenerationService(session)
        target_date = date.today() + timedelta(days=3)

        response = service.insert_emergency_job(
            job_id=uuid4(),
            target_date=target_date,
        )

        assert hasattr(response, "success")
        assert hasattr(response, "job_id")
        assert hasattr(response, "target_date")
        assert hasattr(response, "assigned_staff_id")
        assert hasattr(response, "constraint_violations")
        assert hasattr(response, "message")
        print("  ✓ All required fields present")
        session.close()
        passed += 1
    except AssertionError as e:
        print(f"  ✗ Missing field: {e}")
        failed += 1
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
