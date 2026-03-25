"""StaffLocationService for GPS location tracking via Redis.

Stores and retrieves staff GPS locations with 5-minute TTL.

Validates: CRM Gap Closure Req 41.1, 41.2, 41.5
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from grins_platform.log_config import LoggerMixin

if TYPE_CHECKING:
    from redis.asyncio import Redis


# Redis key pattern and TTL
STAFF_LOCATION_PREFIX = "staff:location:"
STAFF_LOCATION_TTL_SECONDS = 300  # 5 minutes


@dataclass
class StaffLocation:
    """Staff GPS location data."""

    staff_id: UUID
    latitude: float
    longitude: float
    timestamp: str  # ISO format
    appointment_id: UUID | None = None


class StaffLocationService(LoggerMixin):
    """Service for staff GPS location tracking via Redis.

    Stores locations with 5-minute TTL using key pattern
    staff:location:{staff_id}.

    Validates: CRM Gap Closure Req 41.1, 41.2, 41.5
    """

    DOMAIN = "staff"

    def __init__(self, redis_client: Redis | None = None) -> None:
        """Initialize StaffLocationService.

        Args:
            redis_client: Redis client for location storage.
        """
        super().__init__()
        self.redis = redis_client

    async def store_location(
        self,
        staff_id: UUID,
        latitude: float,
        longitude: float,
        appointment_id: UUID | None = None,
    ) -> bool:
        """Store a staff member's GPS location in Redis.

        Args:
            staff_id: Staff UUID.
            latitude: GPS latitude.
            longitude: GPS longitude.
            appointment_id: Current appointment UUID (optional).

        Returns:
            True if stored successfully, False otherwise.

        Validates: Req 41.1
        """
        self.log_started(
            "store_location",
            staff_id=str(staff_id),
        )

        if self.redis is None:
            self.log_rejected(
                "store_location",
                reason="redis_unavailable",
            )
            return False

        from datetime import datetime, timezone  # noqa: PLC0415

        key = f"{STAFF_LOCATION_PREFIX}{staff_id}"
        data = {
            "staff_id": str(staff_id),
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "appointment_id": str(appointment_id) if appointment_id else None,
        }

        try:
            await self.redis.set(
                key,
                json.dumps(data),
                ex=STAFF_LOCATION_TTL_SECONDS,
            )
        except Exception as exc:
            self.log_failed(
                "store_location",
                error=exc,
                staff_id=str(staff_id),
            )
            return False
        else:
            self.log_completed(
                "store_location",
                staff_id=str(staff_id),
            )
            return True

    async def get_location(
        self,
        staff_id: UUID,
    ) -> StaffLocation | None:
        """Retrieve a staff member's current GPS location.

        Args:
            staff_id: Staff UUID.

        Returns:
            StaffLocation if found and not expired, None otherwise.

        Validates: Req 41.2
        """
        if self.redis is None:
            return None

        key = f"{STAFF_LOCATION_PREFIX}{staff_id}"

        try:
            raw = await self.redis.get(key)
            if raw is None:
                return None

            data = json.loads(raw)
            appt_id = data.get("appointment_id")
            return StaffLocation(
                staff_id=UUID(data["staff_id"]),
                latitude=float(data["latitude"]),
                longitude=float(data["longitude"]),
                timestamp=data["timestamp"],
                appointment_id=UUID(appt_id) if appt_id else None,
            )
        except Exception as exc:
            self.log_failed(
                "get_location",
                error=exc,
                staff_id=str(staff_id),
            )
            return None

    async def get_all_locations(
        self,
        staff_ids: list[UUID],
    ) -> list[StaffLocation]:
        """Retrieve current locations for multiple staff members.

        Args:
            staff_ids: List of staff UUIDs.

        Returns:
            List of StaffLocation for staff with active locations.

        Validates: Req 41.5
        """
        locations: list[StaffLocation] = []
        for staff_id in staff_ids:
            loc = await self.get_location(staff_id)
            if loc is not None:
                locations.append(loc)
        return locations
