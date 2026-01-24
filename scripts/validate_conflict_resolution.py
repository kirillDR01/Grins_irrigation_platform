#!/usr/bin/env python3
"""Functional validation script for conflict resolution.

Validates: Requirements 10.1-10.7, 14.5
"""

import sys
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4

# Add src to path for imports
sys.path.insert(0, "src")


def main() -> int:
    """Run conflict resolution validation."""
    print("=" * 60)
    print("Conflict Resolution Functional Validation")
    print("=" * 60)

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from grins_platform.database import DatabaseSettings
    from grins_platform.services.conflict_resolution_service import (
        ConflictResolutionService,
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
    print("\n[Test 1] ConflictResolutionService methods exist")
    try:
        session = session_factory()
        service = ConflictResolutionService(session)

        assert hasattr(service, "cancel_appointment")
        assert hasattr(service, "reschedule_appointment")
        assert hasattr(service, "get_waitlist")
        assert hasattr(service, "fill_gap_suggestions")
        print("  ✓ cancel_appointment method exists")
        print("  ✓ reschedule_appointment method exists")
        print("  ✓ get_waitlist method exists")
        print("  ✓ fill_gap_suggestions method exists")
        session.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 2: Cancel non-existent appointment
    print("\n[Test 2] Cancel non-existent appointment")
    try:
        session = session_factory()
        service = ConflictResolutionService(session)

        response = service.cancel_appointment(
            appointment_id=uuid4(),
            reason="Test cancellation",
        )

        assert response.appointment_id is not None
        assert response.reason == "Test cancellation"
        assert "not found" in response.message.lower()
        print(f"  ✓ Returns response for non-existent appointment")
        print(f"  ✓ Message: {response.message}")
        session.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 3: Get empty waitlist
    print("\n[Test 3] Get waitlist (may be empty)")
    try:
        session = session_factory()
        service = ConflictResolutionService(session)
        target_date = date.today() + timedelta(days=7)

        waitlist = service.get_waitlist(target_date)

        assert isinstance(waitlist, list)
        print(f"  ✓ Waitlist returned: {len(waitlist)} entries")
        session.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 4: Fill gap suggestions
    print("\n[Test 4] Fill gap suggestions")
    try:
        session = session_factory()
        service = ConflictResolutionService(session)
        target_date = date.today() + timedelta(days=1)

        response = service.fill_gap_suggestions(
            target_date=target_date,
            gap_start=time(10, 0),
            gap_end=time(12, 0),
        )

        assert response.target_date == target_date
        assert response.gap_start == time(10, 0)
        assert response.gap_end == time(12, 0)
        assert response.gap_duration_minutes == 120
        assert isinstance(response.suggestions, list)
        print(f"  ✓ Gap duration: {response.gap_duration_minutes} minutes")
        print(f"  ✓ Suggestions: {len(response.suggestions)}")
        session.close()
        passed += 1
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        failed += 1

    # Test 5: CancelAppointmentResponse has required fields
    print("\n[Test 5] CancelAppointmentResponse has required fields")
    try:
        session = session_factory()
        service = ConflictResolutionService(session)

        response = service.cancel_appointment(
            appointment_id=uuid4(),
            reason="Test",
        )

        assert hasattr(response, "appointment_id")
        assert hasattr(response, "cancelled_at")
        assert hasattr(response, "reason")
        assert hasattr(response, "waitlist_entry_id")
        assert hasattr(response, "message")
        print("  ✓ All required fields present")
        session.close()
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
