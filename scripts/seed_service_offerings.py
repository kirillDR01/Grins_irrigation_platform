#!/usr/bin/env python3
"""
Seed script for default service offerings.

This script creates the default service offerings for the Grin's Irrigation Platform.
It is idempotent - running it multiple times will not create duplicates.

Usage:
    uv run python scripts/seed_service_offerings.py

Validates: Requirements 13.1-13.6
"""

from __future__ import annotations

import asyncio
import os
import sys
from decimal import Decimal

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from grins_platform.models.service_offering import ServiceOffering


# Default service offerings based on design.md
DEFAULT_SERVICES = [
    {
        "name": "Spring Startup",
        "category": "seasonal",
        "description": "Spring irrigation system startup and inspection",
        "base_price": Decimal("50.00"),
        "price_per_zone": Decimal("10.00"),
        "pricing_model": "zone_based",
        "estimated_duration_minutes": 30,
        "duration_per_zone_minutes": 5,
        "staffing_required": 1,
        "equipment_required": ["standard_tools"],
        "lien_eligible": False,
        "requires_prepay": False,
    },
    {
        "name": "Summer Tune-up",
        "category": "seasonal",
        "description": "Mid-season irrigation system tune-up and adjustment",
        "base_price": Decimal("50.00"),
        "price_per_zone": Decimal("10.00"),
        "pricing_model": "zone_based",
        "estimated_duration_minutes": 30,
        "duration_per_zone_minutes": 5,
        "staffing_required": 1,
        "equipment_required": ["standard_tools"],
        "lien_eligible": False,
        "requires_prepay": False,
    },
    {
        "name": "Winterization",
        "category": "seasonal",
        "description": "Fall irrigation system winterization with compressed air blowout",
        "base_price": Decimal("60.00"),
        "price_per_zone": Decimal("12.00"),
        "pricing_model": "zone_based",
        "estimated_duration_minutes": 45,
        "duration_per_zone_minutes": 5,
        "staffing_required": 1,
        "equipment_required": ["standard_tools", "compressor"],
        "lien_eligible": False,
        "requires_prepay": False,
    },
    {
        "name": "Head Replacement",
        "category": "repair",
        "description": "Replace broken or damaged sprinkler head",
        "base_price": Decimal("50.00"),
        "price_per_zone": None,
        "pricing_model": "flat",
        "estimated_duration_minutes": 30,
        "duration_per_zone_minutes": None,
        "staffing_required": 1,
        "equipment_required": ["standard_tools"],
        "lien_eligible": False,
        "requires_prepay": False,
    },
    {
        "name": "Diagnostic",
        "category": "diagnostic",
        "description": "System troubleshooting and diagnostic service",
        "base_price": Decimal("100.00"),
        "price_per_zone": None,
        "pricing_model": "hourly",
        "estimated_duration_minutes": 60,
        "duration_per_zone_minutes": None,
        "staffing_required": 1,
        "equipment_required": ["standard_tools", "diagnostic_equipment"],
        "lien_eligible": False,
        "requires_prepay": False,
    },
    {
        "name": "New System Installation",
        "category": "installation",
        "description": "Complete new irrigation system installation",
        "base_price": None,
        "price_per_zone": Decimal("700.00"),
        "pricing_model": "custom",
        "estimated_duration_minutes": None,
        "duration_per_zone_minutes": 120,
        "staffing_required": 2,
        "equipment_required": ["pipe_puller", "utility_trailer", "standard_tools"],
        "lien_eligible": True,
        "requires_prepay": True,
    },
    {
        "name": "Zone Addition",
        "category": "installation",
        "description": "Add new zone to existing irrigation system",
        "base_price": None,
        "price_per_zone": Decimal("500.00"),
        "pricing_model": "custom",
        "estimated_duration_minutes": None,
        "duration_per_zone_minutes": 90,
        "staffing_required": 2,
        "equipment_required": ["pipe_puller", "standard_tools"],
        "lien_eligible": True,
        "requires_prepay": True,
    },
]


async def seed_service_offerings(session: AsyncSession) -> int:
    """Seed default service offerings.

    Args:
        session: Database session

    Returns:
        Number of services created
    """
    created_count = 0

    for service_data in DEFAULT_SERVICES:
        # Check if service already exists by name
        stmt = select(ServiceOffering).where(
            ServiceOffering.name == service_data["name"]
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  Service '{service_data['name']}' already exists, skipping...")
            continue

        # Create new service
        service = ServiceOffering(**service_data)
        session.add(service)
        created_count += 1
        print(f"  Created service: {service_data['name']}")

    await session.commit()
    return created_count


async def main() -> None:
    """Main entry point for seeding."""
    # Get database URL from environment
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://grins:grins_dev_password@localhost:5432/grins_platform",
    )

    print(f"Connecting to database...")
    print(f"  URL: {database_url.split('@')[1] if '@' in database_url else database_url}")

    # Create engine and session
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            print("\nSeeding default service offerings...")
            created = await seed_service_offerings(session)
            print(f"\nSeeding complete! Created {created} new service offerings.")
    except Exception as e:
        print(f"\nError during seeding: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
