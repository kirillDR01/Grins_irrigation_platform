#!/usr/bin/env python3
"""
Test data seeding script for Route Optimization feature.

This script generates realistic test data for the Twin Cities metro area
to support route optimization testing and development.

Generates:
- 20-30 test properties with real Twin Cities coordinates
- 15-25 test jobs with varied types, priorities, equipment needs
- 3-5 test staff with different equipment assignments
- Staff availability for next 7 days

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6
"""

import asyncio
import random
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from grins_platform.database import Base
from grins_platform.models.customer import Customer
from grins_platform.models.enums import (
    CustomerStatus,
    JobCategory,
    JobSource,
    JobStatus,
    LeadSource,
    PricingModel,
    PropertyType,
    ServiceCategory,
    SkillLevel,
    StaffRole,
    SystemType,
)
from grins_platform.models.job import Job
from grins_platform.models.property import Property
from grins_platform.models.service_offering import ServiceOffering
from grins_platform.models.staff import Staff

# =============================================================================
# Twin Cities Coordinates (Real locations)
# =============================================================================

# City center coordinates for the Twin Cities metro area
TWIN_CITIES_LOCATIONS = {
    "Eden Prairie": {
        "center": (44.8547, -93.4708),
        "addresses": [
            ("123 Prairie Center Dr", 44.8547, -93.4708),
            ("456 Flying Cloud Dr", 44.8612, -93.4523),
            ("789 Technology Dr", 44.8489, -93.4891),
            ("321 Eden Prairie Rd", 44.8634, -93.4612),
            ("654 Valley View Rd", 44.8501, -93.4789),
        ],
    },
    "Plymouth": {
        "center": (45.0105, -93.4555),
        "addresses": [
            ("100 Plymouth Blvd", 45.0105, -93.4555),
            ("200 Vicksburg Ln", 45.0234, -93.4678),
            ("300 Harbor Ln", 45.0012, -93.4412),
            ("400 Fernbrook Ln", 45.0189, -93.4823),
            ("500 Rockford Rd", 45.0078, -93.4567),
        ],
    },
    "Maple Grove": {
        "center": (45.0724, -93.4558),
        "addresses": [
            ("600 Main St", 45.0724, -93.4558),
            ("700 Weaver Lake Rd", 45.0812, -93.4423),
            ("800 Elm Creek Blvd", 45.0689, -93.4712),
            ("900 Arbor Lakes Pkwy", 45.0756, -93.4389),
            ("1000 Hemlock Ln", 45.0634, -93.4601),
        ],
    },
    "Brooklyn Park": {
        "center": (45.0941, -93.3563),
        "addresses": [
            ("1100 Brooklyn Blvd", 45.0941, -93.3563),
            ("1200 Zane Ave N", 45.1023, -93.3478),
            ("1300 85th Ave N", 45.0889, -93.3689),
            ("1400 Noble Pkwy", 45.0978, -93.3512),
            ("1500 Regent Ave N", 45.0856, -93.3601),
        ],
    },
    "Rogers": {
        "center": (45.1889, -93.5530),
        "addresses": [
            ("1600 Main St", 45.1889, -93.5530),
            ("1700 Industrial Blvd", 45.1956, -93.5423),
            ("1800 141st Ave N", 45.1823, -93.5678),
            ("1900 Territorial Rd", 45.1912, -93.5389),
            ("2000 Brockton Ln", 45.1789, -93.5512),
        ],
    },
}

# Equipment types for irrigation work
EQUIPMENT_TYPES = [
    "compressor",
    "pipe_puller",
    "utility_trailer",
    "skid_steer",
    "dump_trailer",
    "trencher",
    "backflow_tester",
]

# Job types with their typical characteristics
JOB_TYPES = {
    "spring_startup": {
        "category": JobCategory.READY_TO_SCHEDULE,
        "duration_range": (30, 60),
        "staffing": 1,
        "equipment": [],
        "priority_weight": 0.7,  # 70% normal priority
    },
    "winterization": {
        "category": JobCategory.READY_TO_SCHEDULE,
        "duration_range": (30, 60),
        "staffing": 1,
        "equipment": ["compressor"],
        "priority_weight": 0.7,
    },
    "tune_up": {
        "category": JobCategory.READY_TO_SCHEDULE,
        "duration_range": (45, 90),
        "staffing": 1,
        "equipment": [],
        "priority_weight": 0.8,
    },
    "repair": {
        "category": JobCategory.READY_TO_SCHEDULE,
        "duration_range": (30, 120),
        "staffing": 1,
        "equipment": [],
        "priority_weight": 0.5,
    },
    "diagnostic": {
        "category": JobCategory.REQUIRES_ESTIMATE,
        "duration_range": (60, 120),
        "staffing": 1,
        "equipment": ["backflow_tester"],
        "priority_weight": 0.6,
    },
    "installation": {
        "category": JobCategory.REQUIRES_ESTIMATE,
        "duration_range": (240, 480),
        "staffing": 2,
        "equipment": ["pipe_puller", "utility_trailer"],
        "priority_weight": 0.3,
    },
    "major_repair": {
        "category": JobCategory.REQUIRES_ESTIMATE,
        "duration_range": (120, 240),
        "staffing": 2,
        "equipment": ["pipe_puller"],
        "priority_weight": 0.4,
    },
}

# Staff configurations
STAFF_CONFIGS = [
    {
        "name": "Viktor Grin",
        "role": StaffRole.ADMIN,
        "skill_level": SkillLevel.LEAD,
        "equipment": ["compressor", "pipe_puller", "utility_trailer", "backflow_tester"],
        "start_city": "Eden Prairie",
        "start_address": "8000 Mitchell Rd",
        "start_lat": 44.8612,
        "start_lng": -93.4523,
    },
    {
        "name": "Vas Technician",
        "role": StaffRole.TECH,
        "skill_level": SkillLevel.SENIOR,
        "equipment": ["compressor", "pipe_puller", "utility_trailer"],
        "start_city": "Plymouth",
        "start_address": "3500 Vicksburg Ln",
        "start_lat": 45.0234,
        "start_lng": -93.4678,
    },
    {
        "name": "Dad Technician",
        "role": StaffRole.TECH,
        "skill_level": SkillLevel.SENIOR,
        "equipment": ["compressor"],
        "start_city": "Maple Grove",
        "start_address": "7500 Main St",
        "start_lat": 45.0724,
        "start_lng": -93.4558,
    },
    {
        "name": "Steven Helper",
        "role": StaffRole.TECH,
        "skill_level": SkillLevel.JUNIOR,
        "equipment": ["compressor", "pipe_puller"],
        "start_city": "Brooklyn Park",
        "start_address": "6800 Brooklyn Blvd",
        "start_lat": 45.0941,
        "start_lng": -93.3563,
    },
]


def generate_phone() -> str:
    """Generate a random 10-digit phone number."""
    return f"612{random.randint(1000000, 9999999)}"


def generate_email(first_name: str, last_name: str) -> str:
    """Generate an email address."""
    domains = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com"]
    return f"{first_name.lower()}.{last_name.lower()}@{random.choice(domains)}"


async def seed_customers_and_properties(session: AsyncSession) -> list[tuple[Customer, Property]]:
    """Create test customers with properties across Twin Cities.
    
    Returns list of (customer, property) tuples.
    """
    print("Creating customers and properties...")
    
    customer_properties = []
    first_names = [
        "John", "Jane", "Michael", "Sarah", "David", "Emily", "Robert", "Lisa",
        "William", "Jennifer", "James", "Amanda", "Thomas", "Jessica", "Daniel",
        "Ashley", "Christopher", "Nicole", "Matthew", "Stephanie", "Andrew", "Melissa",
        "Joseph", "Rebecca", "Charles", "Laura", "Kevin", "Michelle", "Brian", "Kimberly",
    ]
    last_names = [
        "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
        "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
        "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
        "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson",
    ]
    
    # Distribute properties across cities
    all_addresses = []
    for city, data in TWIN_CITIES_LOCATIONS.items():
        for addr, lat, lng in data["addresses"]:
            all_addresses.append((city, addr, lat, lng))
    
    # Shuffle and select 25 addresses
    random.shuffle(all_addresses)
    selected_addresses = all_addresses[:25]
    
    for i, (city, address, lat, lng) in enumerate(selected_addresses):
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        
        # Create customer
        customer = Customer(
            first_name=first_name,
            last_name=last_name,
            phone=generate_phone(),
            email=generate_email(first_name, last_name),
            status=CustomerStatus.ACTIVE.value,
            is_priority=random.random() < 0.2,  # 20% priority
            is_red_flag=random.random() < 0.05,  # 5% red flag
            is_slow_payer=random.random() < 0.1,  # 10% slow payer
            is_new_customer=random.random() < 0.3,  # 30% new
            sms_opt_in=random.random() < 0.7,  # 70% SMS opt-in
            email_opt_in=random.random() < 0.5,  # 50% email opt-in
            lead_source=random.choice([s.value for s in LeadSource]),
        )
        session.add(customer)
        await session.flush()  # Get customer ID
        
        # Create property
        prop = Property(
            customer_id=customer.id,
            address=address,
            city=city,
            state="MN",
            zip_code=f"55{random.randint(100, 999)}",
            latitude=Decimal(str(lat)),
            longitude=Decimal(str(lng)),
            zone_count=random.randint(4, 12),
            system_type=random.choice([SystemType.STANDARD.value, SystemType.LAKE_PUMP.value]),
            property_type=random.choice([PropertyType.RESIDENTIAL.value, PropertyType.COMMERCIAL.value]),
            is_primary=True,
            access_instructions=random.choice([
                None,
                "Gate code required",
                "Enter through side gate",
                "Ring doorbell on arrival",
            ]),
            gate_code=f"{random.randint(1000, 9999)}" if random.random() < 0.3 else None,
            has_dogs=random.random() < 0.25,  # 25% have dogs
            special_notes=random.choice([
                None,
                "Elderly customer - be patient",
                "Commercial property - check in at office",
                "Lake pump system - extra time needed",
            ]),
        )
        session.add(prop)
        customer_properties.append((customer, prop))
    
    await session.commit()
    print(f"  Created {len(customer_properties)} customers with properties")
    return customer_properties


async def seed_service_offerings(session: AsyncSession) -> dict[str, ServiceOffering]:
    """Create or get service offerings for job creation."""
    print("Checking service offerings...")
    
    # Check if service offerings exist
    result = await session.execute(select(ServiceOffering))
    existing = {s.name: s for s in result.scalars().all()}
    
    if existing:
        print(f"  Found {len(existing)} existing service offerings")
        return existing
    
    # Create service offerings if none exist
    offerings = {}
    service_data = [
        ("Spring Startup", ServiceCategory.SEASONAL, PricingModel.ZONE_BASED, 45, 5, 1, []),
        ("Winterization", ServiceCategory.SEASONAL, PricingModel.ZONE_BASED, 45, 5, 1, ["compressor"]),
        ("Summer Tune-Up", ServiceCategory.SEASONAL, PricingModel.ZONE_BASED, 60, 8, 1, []),
        ("Sprinkler Head Repair", ServiceCategory.REPAIR, PricingModel.FLAT, 30, 0, 1, []),
        ("Diagnostic Service", ServiceCategory.DIAGNOSTIC, PricingModel.HOURLY, 60, 0, 1, ["backflow_tester"]),
        ("New Installation", ServiceCategory.INSTALLATION, PricingModel.ZONE_BASED, 240, 30, 2, ["pipe_puller", "utility_trailer"]),
        ("Major Repair", ServiceCategory.REPAIR, PricingModel.CUSTOM, 120, 0, 2, ["pipe_puller"]),
    ]
    
    for name, category, pricing, duration, per_zone, staffing, equipment in service_data:
        offering = ServiceOffering(
            name=name,
            category=category.value,
            pricing_model=pricing.value,
            estimated_duration_minutes=duration,
            duration_per_zone_minutes=per_zone,
            staffing_required=staffing,
            equipment_required=equipment if equipment else None,
            base_price=Decimal("50.00") if pricing == PricingModel.FLAT else None,
            price_per_zone=Decimal("15.00") if pricing == PricingModel.ZONE_BASED else None,
            is_active=True,
        )
        session.add(offering)
        offerings[name] = offering
    
    await session.commit()
    print(f"  Created {len(offerings)} service offerings")
    return offerings


async def seed_jobs(
    session: AsyncSession,
    customer_properties: list[tuple[Customer, Property]],
    service_offerings: dict[str, ServiceOffering],
) -> list[Job]:
    """Create test jobs with varied types, priorities, and equipment needs."""
    print("Creating jobs...")
    
    jobs = []
    job_type_mapping = {
        "spring_startup": "Spring Startup",
        "winterization": "Winterization",
        "tune_up": "Summer Tune-Up",
        "repair": "Sprinkler Head Repair",
        "diagnostic": "Diagnostic Service",
        "installation": "New Installation",
        "major_repair": "Major Repair",
    }
    
    # Create 20 jobs distributed across properties
    num_jobs = 20
    for i in range(num_jobs):
        customer, prop = random.choice(customer_properties)
        job_type = random.choice(list(JOB_TYPES.keys()))
        job_config = JOB_TYPES[job_type]
        
        # Determine priority based on weight
        if random.random() > job_config["priority_weight"]:
            priority = random.choice([1, 2])  # High or urgent
        else:
            priority = 0  # Normal
        
        # Get service offering if available
        service_name = job_type_mapping.get(job_type)
        service_offering = service_offerings.get(service_name) if service_name else None
        
        # Calculate duration
        min_dur, max_dur = job_config["duration_range"]
        base_duration = random.randint(min_dur, max_dur)
        # Add zone-based time for zone-based services
        if job_type in ["spring_startup", "winterization", "tune_up"]:
            base_duration += (prop.zone_count or 6) * 5
        
        job = Job(
            customer_id=customer.id,
            property_id=prop.id,
            service_offering_id=service_offering.id if service_offering else None,
            job_type=job_type,
            category=job_config["category"].value,
            status=JobStatus.APPROVED.value,  # Ready for scheduling
            description=f"Test {job_type.replace('_', ' ')} job for route optimization testing",
            estimated_duration_minutes=base_duration,
            priority_level=priority,
            weather_sensitive=job_type in ["installation", "major_repair"],
            staffing_required=job_config["staffing"],
            equipment_required=job_config["equipment"] if job_config["equipment"] else None,
            source=random.choice([s.value for s in JobSource]),
            requested_at=datetime.now() - timedelta(days=random.randint(1, 7)),
            approved_at=datetime.now() - timedelta(hours=random.randint(1, 48)),
        )
        session.add(job)
        jobs.append(job)
    
    await session.commit()
    print(f"  Created {len(jobs)} jobs")
    return jobs


async def seed_staff(session: AsyncSession) -> list[Staff]:
    """Create test staff with different equipment assignments."""
    print("Creating staff...")
    
    # Check if staff exist
    result = await session.execute(select(Staff))
    existing = list(result.scalars().all())
    
    if existing:
        print(f"  Found {len(existing)} existing staff members")
        return existing
    
    staff_list = []
    for config in STAFF_CONFIGS:
        staff = Staff(
            name=config["name"],
            phone=generate_phone(),
            email=f"{config['name'].lower().replace(' ', '.')}@grins.com",
            role=config["role"].value,
            skill_level=config["skill_level"].value,
            certifications=["irrigation_certified"] if config["skill_level"] != SkillLevel.JUNIOR else None,
            is_available=True,
            hourly_rate=Decimal("35.00") if config["skill_level"] == SkillLevel.JUNIOR else Decimal("50.00"),
            is_active=True,
        )
        session.add(staff)
        staff_list.append(staff)
    
    await session.commit()
    print(f"  Created {len(staff_list)} staff members")
    return staff_list


async def seed_staff_availability(session: AsyncSession, staff: list[Staff]) -> int:
    """Create staff availability entries for the next 7 days.
    
    Note: This function requires the staff_availability table to exist.
    Run after Task 2.1 migration is applied.
    
    Requirements: 13.4, 13.5
    """
    print("Creating staff availability...")
    
    # Try to import StaffAvailability model (may not exist yet)
    try:
        from grins_platform.models.staff_availability import StaffAvailability
    except ImportError:
        print("  ⚠️  StaffAvailability model not found - skipping availability seeding")
        print("     Run this script again after Task 2.1-2.2 are complete")
        return 0
    
    # Check if table exists by trying a simple query
    try:
        from sqlalchemy import text
        await session.execute(text("SELECT 1 FROM staff_availability LIMIT 1"))
    except Exception:
        print("  ⚠️  staff_availability table not found - skipping availability seeding")
        print("     Run this script again after Task 2.1 migration is applied")
        return 0
    
    availability_count = 0
    today = date.today()
    
    # Varied lunch times for different staff
    lunch_configs = [
        (time(12, 0), 30),   # 12:00, 30 min
        (time(12, 30), 45),  # 12:30, 45 min
        (time(11, 30), 30),  # 11:30, 30 min
        (time(13, 0), 60),   # 13:00, 60 min
    ]
    
    # Varied availability windows
    availability_windows = [
        (time(7, 0), time(17, 0)),   # Standard 7am-5pm
        (time(7, 30), time(16, 30)), # 7:30am-4:30pm
        (time(8, 0), time(18, 0)),   # 8am-6pm
        (time(6, 30), time(15, 30)), # Early bird 6:30am-3:30pm
    ]
    
    for i, staff_member in enumerate(staff):
        lunch_start, lunch_duration = lunch_configs[i % len(lunch_configs)]
        start_time, end_time = availability_windows[i % len(availability_windows)]
        
        # Create availability for next 7 days
        for day_offset in range(7):
            target_date = today + timedelta(days=day_offset)
            
            # Skip weekends for some staff (simulate real schedules)
            is_weekend = target_date.weekday() >= 5
            if is_weekend and i > 1:  # Only Viktor and Vas work weekends
                continue
            
            # Check if availability already exists
            from sqlalchemy import and_
            existing = await session.execute(
                select(StaffAvailability).where(
                    and_(
                        StaffAvailability.staff_id == staff_member.id,
                        StaffAvailability.date == target_date,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue
            
            availability = StaffAvailability(
                staff_id=staff_member.id,
                date=target_date,
                start_time=start_time,
                end_time=end_time,
                is_available=True,
                lunch_start=lunch_start,
                lunch_duration_minutes=lunch_duration,
                notes=f"Auto-generated availability for {staff_member.name}",
            )
            session.add(availability)
            availability_count += 1
    
    await session.commit()
    print(f"  Created {availability_count} availability entries")
    return availability_count


def print_summary(
    customer_properties: list[tuple[Customer, Property]],
    jobs: list[Job],
    staff: list[Staff],
    availability_count: int = 0,
) -> None:
    """Print summary of seeded data."""
    print("\n" + "=" * 60)
    print("ROUTE OPTIMIZATION TEST DATA SUMMARY")
    print("=" * 60)
    
    print(f"\nCustomers & Properties: {len(customer_properties)}")
    cities = {}
    for _, prop in customer_properties:
        cities[prop.city] = cities.get(prop.city, 0) + 1
    for city, count in sorted(cities.items()):
        print(f"  - {city}: {count} properties")
    
    print(f"\nJobs: {len(jobs)}")
    job_types = {}
    priorities = {0: 0, 1: 0, 2: 0}
    for job in jobs:
        job_types[job.job_type] = job_types.get(job.job_type, 0) + 1
        priorities[job.priority_level] = priorities.get(job.priority_level, 0) + 1
    for jt, count in sorted(job_types.items()):
        print(f"  - {jt}: {count}")
    print(f"  Priority: Normal={priorities[0]}, High={priorities[1]}, Urgent={priorities[2]}")
    
    print(f"\nStaff: {len(staff)}")
    for s in staff:
        print(f"  - {s.name} ({s.role}, {s.skill_level})")
    
    if availability_count > 0:
        print(f"\nStaff Availability: {availability_count} entries (next 7 days)")
    
    print("\n" + "=" * 60)


async def main() -> None:
    """Main entry point for seeding test data."""
    import os
    
    # Get database URL from environment
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://grins_user:grins_password@localhost:5432/grins_platform",
    )
    
    # Convert to async URL if needed
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    print(f"Connecting to database...")
    
    # Create async engine
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Seed data
            customer_properties = await seed_customers_and_properties(session)
            service_offerings = await seed_service_offerings(session)
            jobs = await seed_jobs(session, customer_properties, service_offerings)
            staff = await seed_staff(session)
            
            # Seed staff availability (requires Task 2.1-2.2 to be complete)
            availability_count = await seed_staff_availability(session, staff)
            
            # Print summary
            print_summary(customer_properties, jobs, staff, availability_count)
            
            print("\n✅ Test data seeding complete!")
            
        except Exception as e:
            print(f"\n❌ Error seeding data: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
