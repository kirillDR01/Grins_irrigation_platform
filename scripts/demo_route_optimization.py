#!/usr/bin/env python3
"""
Route Optimization Full Demo Script.

This script demonstrates the complete route optimization workflow:
1. Check scheduling capacity
2. Generate optimized schedule
3. View assignments with travel times
4. Insert emergency job
5. Re-optimize schedule

Prerequisites:
- Docker running with PostgreSQL
- Test data seeded (run seed_route_optimization_test_data.py first)
"""

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx

BASE_URL = "http://localhost:8000/api/v1"


def print_header(title: str) -> None:
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n--- {title} ---")


async def check_health() -> bool:
    """Check if the API is running."""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{BASE_URL.replace('/api/v1', '')}/health")
            return resp.status_code == 200
        except Exception:
            return False


async def get_capacity(target_date: date) -> dict | None:
    """Get scheduling capacity for a date."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/schedule/capacity/{target_date}")
        if resp.status_code == 200:
            return resp.json()
        print(f"  Error: {resp.status_code} - {resp.text}")
        return None


async def generate_schedule(target_date: date, timeout: int = 30) -> dict | None:
    """Generate optimized schedule."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{BASE_URL}/schedule/generate",
            json={"schedule_date": str(target_date), "timeout_seconds": timeout},
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"  Error: {resp.status_code} - {resp.text}")
        return None


async def preview_schedule(target_date: date, timeout: int = 15) -> dict | None:
    """Preview schedule without persisting."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{BASE_URL}/schedule/preview",
            json={"schedule_date": str(target_date), "timeout_seconds": timeout},
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"  Error: {resp.status_code} - {resp.text}")
        return None


async def insert_emergency(job_id: str, target_date: date, priority: int = 1) -> dict | None:
    """Insert emergency job."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{BASE_URL}/schedule/insert-emergency",
            json={
                "job_id": job_id,
                "target_date": str(target_date),
                "priority_level": priority,
            },
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"  Error: {resp.status_code} - {resp.text}")
        return None


async def reoptimize(target_date: date, timeout: int = 15) -> dict | None:
    """Re-optimize existing schedule."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        # The endpoint expects target_date in the body, not just path
        resp = await client.post(
            f"{BASE_URL}/schedule/re-optimize/{target_date}",
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"  Error: {resp.status_code} - {resp.text}")
        return None


async def get_jobs(status: str = "approved") -> list[dict]:
    """Get jobs by status."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/jobs", params={"status": status, "page_size": 50})
        if resp.status_code == 200:
            return resp.json().get("items", [])
        return []


async def get_staff() -> list[dict]:
    """Get all staff."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/staff", params={"page_size": 50})
        if resp.status_code == 200:
            return resp.json().get("items", [])
        return []


def display_capacity(capacity: dict) -> None:
    """Display capacity information."""
    print(f"  Schedule Date: {capacity['schedule_date']}")
    print(f"  Total Staff: {capacity.get('total_staff', 'N/A')}")
    print(f"  Available Staff: {capacity['available_staff']}")
    print(f"  Total Capacity: {capacity['total_capacity_minutes']} minutes")
    print(f"  Scheduled: {capacity.get('scheduled_minutes', 0)} minutes")
    print(f"  Remaining Capacity: {capacity['remaining_capacity_minutes']} minutes")
    print(f"  Can Accept More: {'✅ Yes' if capacity.get('can_accept_more', True) else '❌ No'}")


def display_schedule(schedule: dict) -> None:
    """Display schedule results."""
    print(f"  Feasible: {'✅ Yes' if schedule['is_feasible'] else '⚠️  No (constraints violated)'}")
    print(f"  Hard Score: {schedule.get('hard_score', 'N/A')}")
    print(f"  Soft Score: {schedule.get('soft_score', 'N/A')}")
    
    assignments = schedule.get("assignments", [])
    unassigned = schedule.get("unassigned_jobs", [])
    
    total_assigned = sum(len(a.get("jobs", [])) for a in assignments)
    total_travel = sum(
        sum(j.get("travel_time_minutes", 0) for j in a.get("jobs", []))
        for a in assignments
    )
    
    print(f"  Total Jobs Assigned: {total_assigned}")
    print(f"  Total Unassigned: {len(unassigned)}")
    print(f"  Total Travel Time: {total_travel} minutes")
    
    if assignments:
        print_section("Staff Assignments")
        for assignment in assignments:
            jobs = assignment.get("jobs", [])
            work_time = sum(j.get("duration_minutes", 0) for j in jobs)
            travel_time = sum(j.get("travel_time_minutes", 0) for j in jobs)
            
            print(f"\n  👷 {assignment['staff_name']}")
            print(f"     Jobs: {len(jobs)}")
            print(f"     Work Time: {work_time} min")
            print(f"     Travel Time: {travel_time} min")
            
            for i, job in enumerate(jobs[:5], 1):  # Show first 5 jobs
                print(f"     {i}. {job.get('customer_name', 'Unknown')} @ {job.get('start_time', 'TBD')}")
                print(f"        📍 {job.get('address', '')}, {job.get('city', '')}")
                print(f"        ⏱️  Duration: {job.get('duration_minutes', 0)} min, Travel: {job.get('travel_time_minutes', 0)} min")
            
            if len(jobs) > 5:
                print(f"     ... and {len(jobs) - 5} more jobs")
    
    if unassigned:
        print_section(f"Unassigned Jobs ({len(unassigned)})")
        for job in unassigned[:3]:  # Show first 3
            print(f"  ❌ {job.get('job_id', 'Unknown')[:8]}... - {job.get('reason', 'No reason')}")
        if len(unassigned) > 3:
            print(f"  ... and {len(unassigned) - 3} more unassigned")


async def run_demo() -> None:
    """Run the full route optimization demo."""
    print_header("GRINS IRRIGATION - ROUTE OPTIMIZATION DEMO")
    
    # Check API health
    print_section("Step 0: Checking API Health")
    if not await check_health():
        print("  ❌ API is not running!")
        print("  Please start the server: uv run uvicorn grins_platform.main:app --reload")
        return
    print("  ✅ API is healthy")
    
    # Use tomorrow's date for demo
    target_date = date.today() + timedelta(days=1)
    print(f"\n  Target Date: {target_date}")
    
    # Step 1: Check capacity
    print_header("STEP 1: Check Scheduling Capacity")
    capacity = await get_capacity(target_date)
    if capacity:
        display_capacity(capacity)
    else:
        print("  ⚠️  Could not get capacity. Continuing anyway...")
    
    # Step 2: Preview schedule
    print_header("STEP 2: Preview Schedule (No Persist)")
    print("  Generating preview with 15-second solver timeout...")
    preview = await preview_schedule(target_date, timeout=15)
    if preview:
        display_schedule(preview)
    else:
        print("  ⚠️  Preview failed")
    
    # Step 3: Generate and persist schedule
    print_header("STEP 3: Generate & Persist Schedule")
    print("  Generating schedule with 30-second solver timeout...")
    schedule = await generate_schedule(target_date, timeout=30)
    if schedule:
        display_schedule(schedule)
    else:
        print("  ⚠️  Schedule generation failed")
        return
    
    # Step 4: Check updated capacity
    print_header("STEP 4: Check Updated Capacity")
    capacity = await get_capacity(target_date)
    if capacity:
        display_capacity(capacity)
    
    # Step 5: Emergency insertion (if we have unassigned jobs)
    print_header("STEP 5: Emergency Job Insertion")
    jobs = await get_jobs("approved")
    if jobs:
        emergency_job = jobs[0]
        print(f"  Inserting emergency job: {emergency_job['id'][:8]}...")
        result = await insert_emergency(emergency_job["id"], target_date, priority=1)
        if result:
            print(f"  Success: {result.get('success', False)}")
            if result.get("assignment"):
                print(f"  Assigned to: {result['assignment'].get('staff_name', 'Unknown')}")
                print(f"  Start time: {result['assignment'].get('start_time', 'TBD')}")
        else:
            print("  ⚠️  Emergency insertion not available or failed")
    else:
        print("  No approved jobs available for emergency insertion demo")
    
    # Step 6: Re-optimize
    print_header("STEP 6: Re-Optimize Schedule")
    print("  Re-optimizing with 15-second timeout...")
    reopt = await reoptimize(target_date, timeout=15)
    if reopt:
        display_schedule(reopt)
    else:
        print("  ⚠️  Re-optimization failed")
    
    # Summary
    print_header("DEMO COMPLETE")
    print("""
  The route optimization system demonstrated:
  
  ✅ Capacity checking - Know available resources before scheduling
  ✅ Schedule preview - Test without committing changes
  ✅ Schedule generation - Optimize job assignments with travel times
  ✅ Emergency insertion - Handle urgent jobs mid-day
  ✅ Re-optimization - Improve schedule after changes
  
  Key Features:
  • Constraint-based optimization (Timefold solver)
  • Travel time estimation between jobs
  • Equipment matching (staff skills → job requirements)
  • Staff availability windows
  • Geographic clustering for efficiency
    """)


if __name__ == "__main__":
    asyncio.run(run_demo())
