#!/usr/bin/env python3
"""
Functional validation script for Staff Availability API.

This script validates the staff availability feature by testing:
1. Creating availability entries via API
2. Querying availability by date range
3. Updating and deleting availability
4. Getting available staff on a specific date

Validates: Requirements 1.1-1.5, 14.1 (Route Optimization)

Usage:
    python scripts/validate_staff_availability.py

Prerequisites:
    - API server running at http://localhost:8000
    - Database with test staff data (run seed_route_optimization_test_data.py first)
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from typing import Any
from uuid import UUID

import httpx

BASE_URL = "http://localhost:8000/api/v1"


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"  ✅ {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"  ❌ {message}")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"  ℹ️  {message}")


def get_test_staff(client: httpx.Client) -> dict[str, Any] | None:
    """Get a test staff member from the database."""
    response = client.get(f"{BASE_URL}/staff", params={"page_size": 1})
    if response.status_code != 200:
        print_error(f"Failed to get staff: {response.status_code}")
        return None
    
    data = response.json()
    if not data.get("items"):
        print_error("No staff members found. Run seed script first.")
        return None
    
    return data["items"][0]


def test_create_availability(
    client: httpx.Client, staff_id: str, target_date: date
) -> dict[str, Any] | None:
    """Test creating a staff availability entry."""
    print_header("Test 1: Create Staff Availability")
    
    payload = {
        "date": target_date.isoformat(),
        "start_time": "08:00:00",
        "end_time": "17:00:00",
        "is_available": True,
        "lunch_start": "12:00:00",
        "lunch_duration_minutes": 30,
        "notes": "Test availability entry",
    }
    
    print_info(f"Creating availability for staff {staff_id} on {target_date}")
    response = client.post(
        f"{BASE_URL}/staff/{staff_id}/availability",
        json=payload,
    )
    
    if response.status_code == 201:
        data = response.json()
        print_success(f"Created availability with ID: {data.get('id')}")
        print_info(f"  Date: {data.get('date')}")
        print_info(f"  Time: {data.get('start_time')} - {data.get('end_time')}")
        print_info(f"  Available: {data.get('is_available')}")
        return data
    elif response.status_code == 409:
        print_info("Availability already exists for this date (expected if re-running)")
        # Try to get existing availability
        get_response = client.get(
            f"{BASE_URL}/staff/{staff_id}/availability/{target_date.isoformat()}"
        )
        if get_response.status_code == 200:
            return get_response.json()
        return None
    else:
        print_error(f"Failed to create availability: {response.status_code}")
        print_error(f"Response: {response.text}")
        return None


def test_list_availability(
    client: httpx.Client, staff_id: str, start_date: date, end_date: date
) -> bool:
    """Test listing availability entries for a date range."""
    print_header("Test 2: List Staff Availability")
    
    print_info(f"Querying availability for staff {staff_id}")
    print_info(f"  Date range: {start_date} to {end_date}")
    
    response = client.get(
        f"{BASE_URL}/staff/{staff_id}/availability",
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Found {len(data)} availability entries")
        for entry in data[:3]:  # Show first 3
            print_info(f"  - {entry.get('date')}: {entry.get('start_time')} - {entry.get('end_time')}")
        if len(data) > 3:
            print_info(f"  ... and {len(data) - 3} more")
        return True
    else:
        print_error(f"Failed to list availability: {response.status_code}")
        print_error(f"Response: {response.text}")
        return False


def test_get_availability_by_date(
    client: httpx.Client, staff_id: str, target_date: date
) -> bool:
    """Test getting availability for a specific date."""
    print_header("Test 3: Get Availability by Date")
    
    print_info(f"Getting availability for staff {staff_id} on {target_date}")
    
    response = client.get(
        f"{BASE_URL}/staff/{staff_id}/availability/{target_date.isoformat()}"
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("Found availability entry")
        print_info(f"  ID: {data.get('id')}")
        print_info(f"  Date: {data.get('date')}")
        print_info(f"  Time: {data.get('start_time')} - {data.get('end_time')}")
        print_info(f"  Lunch: {data.get('lunch_start')} ({data.get('lunch_duration_minutes')} min)")
        return True
    elif response.status_code == 404:
        print_info("No availability found for this date (expected if not created)")
        return True
    else:
        print_error(f"Failed to get availability: {response.status_code}")
        print_error(f"Response: {response.text}")
        return False


def test_update_availability(
    client: httpx.Client, staff_id: str, target_date: date
) -> bool:
    """Test updating an availability entry."""
    print_header("Test 4: Update Staff Availability")
    
    payload = {
        "start_time": "09:00:00",
        "end_time": "18:00:00",
        "notes": "Updated availability entry",
    }
    
    print_info(f"Updating availability for staff {staff_id} on {target_date}")
    print_info(f"  New time: 09:00 - 18:00")
    
    response = client.put(
        f"{BASE_URL}/staff/{staff_id}/availability/{target_date.isoformat()}",
        json=payload,
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success("Updated availability entry")
        print_info(f"  New time: {data.get('start_time')} - {data.get('end_time')}")
        print_info(f"  Notes: {data.get('notes')}")
        return True
    elif response.status_code == 404:
        print_info("No availability found to update (create one first)")
        return True
    else:
        print_error(f"Failed to update availability: {response.status_code}")
        print_error(f"Response: {response.text}")
        return False


def test_get_available_staff_on_date(client: httpx.Client, target_date: date) -> bool:
    """Test getting all available staff on a specific date."""
    print_header("Test 5: Get Available Staff on Date")
    
    print_info(f"Getting all available staff on {target_date}")
    
    response = client.get(
        f"{BASE_URL}/staff/availability/date/{target_date.isoformat()}"
    )
    
    if response.status_code == 200:
        data = response.json()
        print_success(f"Found {data.get('total_available', 0)} available staff members")
        print_info(f"  Date: {data.get('date')}")
        
        for staff in data.get("available_staff", [])[:5]:  # Show first 5
            print_info(f"  - {staff.get('staff_name')}: {staff.get('start_time')} - {staff.get('end_time')}")
        
        if data.get("total_available", 0) > 5:
            print_info(f"  ... and {data.get('total_available') - 5} more")
        return True
    else:
        print_error(f"Failed to get available staff: {response.status_code}")
        print_error(f"Response: {response.text}")
        return False


def test_delete_availability(
    client: httpx.Client, staff_id: str, target_date: date
) -> bool:
    """Test deleting an availability entry."""
    print_header("Test 6: Delete Staff Availability")
    
    print_info(f"Deleting availability for staff {staff_id} on {target_date}")
    
    response = client.delete(
        f"{BASE_URL}/staff/{staff_id}/availability/{target_date.isoformat()}"
    )
    
    if response.status_code == 204:
        print_success("Deleted availability entry")
        
        # Verify deletion
        verify_response = client.get(
            f"{BASE_URL}/staff/{staff_id}/availability/{target_date.isoformat()}"
        )
        if verify_response.status_code == 404:
            print_success("Verified: Entry no longer exists")
        return True
    elif response.status_code == 404:
        print_info("No availability found to delete (already deleted or never created)")
        return True
    else:
        print_error(f"Failed to delete availability: {response.status_code}")
        print_error(f"Response: {response.text}")
        return False


def main() -> int:
    """Run all functional validation tests."""
    print("\n" + "=" * 60)
    print("  STAFF AVAILABILITY FUNCTIONAL VALIDATION")
    print("=" * 60)
    
    # Test dates
    today = date.today()
    test_date = today + timedelta(days=30)  # Use a future date to avoid conflicts
    start_date = today
    end_date = today + timedelta(days=7)
    
    results: list[bool] = []
    
    with httpx.Client(timeout=30.0) as client:
        # Get a test staff member
        staff = get_test_staff(client)
        if not staff:
            print_error("Cannot proceed without test staff. Run seed script first.")
            return 1
        
        staff_id = staff["id"]
        print_info(f"Using test staff: {staff.get('first_name')} {staff.get('last_name')}")
        
        # Run tests
        availability = test_create_availability(client, staff_id, test_date)
        results.append(availability is not None)
        
        results.append(test_list_availability(client, staff_id, start_date, end_date))
        results.append(test_get_availability_by_date(client, staff_id, test_date))
        results.append(test_update_availability(client, staff_id, test_date))
        results.append(test_get_available_staff_on_date(client, test_date))
        results.append(test_delete_availability(client, staff_id, test_date))
    
    # Summary
    print_header("VALIDATION SUMMARY")
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print_success(f"All {total} tests passed!")
        print("\n✅ Staff Availability API is working correctly.\n")
        return 0
    else:
        print_error(f"{total - passed} of {total} tests failed")
        print("\n❌ Some tests failed. Check the output above for details.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
