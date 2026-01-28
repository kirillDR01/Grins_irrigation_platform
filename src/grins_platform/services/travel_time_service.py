"""
Travel time calculation service for route optimization.

This module provides travel time calculations using Google Maps Distance
Matrix API with fallback to haversine formula.

Validates: Requirements 4.1-4.5 (Route Optimization)
"""

from __future__ import annotations

import math
import os
from typing import TYPE_CHECKING

import httpx

from grins_platform.log_config import LoggerMixin

if TYPE_CHECKING:
    from datetime import datetime


# Earth radius in kilometers
EARTH_RADIUS_KM = 6371.0

# Average driving speed for fallback calculation (km/h)
AVERAGE_SPEED_KMH = 40.0

# Road factor (roads are ~1.4x longer than straight line)
ROAD_FACTOR = 1.4

# Default travel time when calculation fails (minutes)
DEFAULT_TRAVEL_TIME_MINUTES = 60


class TravelTimeService(LoggerMixin):
    """Service for calculating travel times between locations.

    Uses Google Maps Distance Matrix API when available, with fallback
    to haversine formula calculation.

    Validates: Requirements 4.1-4.5
    """

    DOMAIN = "business"

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the travel time service.

        Args:
            api_key: Google Maps API key (optional, uses env var if not provided)
        """
        self.api_key = api_key or os.getenv("GOOGLE_MAPS_API_KEY")
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_travel_time(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        departure_time: datetime | None = None,
    ) -> int:
        """Get driving time in minutes between two points.

        Args:
            origin: (latitude, longitude) of origin
            destination: (latitude, longitude) of destination
            departure_time: Optional departure time for traffic estimation

        Returns:
            Travel time in minutes

        Validates: Requirements 4.1, 4.2, 4.5
        """
        self.log_started(
            "get_travel_time",
            origin=origin,
            destination=destination,
        )

        # Try Google Maps API first
        if self.api_key:
            try:
                travel_time = await self._get_google_travel_time(
                    origin,
                    destination,
                    departure_time,
                )
            except Exception as e:
                self.log_failed(
                    "get_travel_time",
                    error=e,
                    fallback="haversine",
                )
            else:
                self.log_completed(
                    "get_travel_time",
                    minutes=travel_time,
                    source="google",
                )
                return travel_time

        # Fallback to haversine calculation
        travel_time = self.calculate_fallback_travel_time(origin, destination)
        self.log_completed("get_travel_time", minutes=travel_time, source="fallback")
        return travel_time

    async def _get_google_travel_time(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
        departure_time: datetime | None = None,
    ) -> int:
        """Get travel time from Google Maps Distance Matrix API.

        Args:
            origin: (latitude, longitude) of origin
            destination: (latitude, longitude) of destination
            departure_time: Optional departure time

        Returns:
            Travel time in minutes

        Raises:
            Exception: If API call fails
        """
        client = await self._get_client()

        params: dict[str, str] = {
            "origins": f"{origin[0]},{origin[1]}",
            "destinations": f"{destination[0]},{destination[1]}",
            "key": self.api_key or "",
            "mode": "driving",
            "units": "imperial",
        }

        if departure_time:
            params["departure_time"] = str(int(departure_time.timestamp()))

        response = await client.get(
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            params=params,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("status") != "OK":
            msg = f"Google Maps API error: {data.get('status')}"
            raise ValueError(msg)

        element = data["rows"][0]["elements"][0]
        if element.get("status") != "OK":
            msg = f"Route not found: {element.get('status')}"
            raise ValueError(msg)

        # Duration is in seconds, convert to minutes
        duration_seconds: int = element["duration"]["value"]
        return math.ceil(duration_seconds / 60)

    async def get_travel_matrix(
        self,
        locations: list[tuple[float, float]],
    ) -> dict[tuple[int, int], int]:
        """Get travel times between all pairs of locations.

        Args:
            locations: List of (latitude, longitude) tuples

        Returns:
            Dictionary mapping (from_index, to_index) to travel time in minutes

        Validates: Requirement 4.3
        """
        self.log_started("get_travel_matrix", location_count=len(locations))

        matrix: dict[tuple[int, int], int] = {}

        # Try Google Maps batch API
        if self.api_key and len(locations) <= 25:  # API limit
            try:
                matrix = await self._get_google_travel_matrix(locations)
            except Exception as e:
                self.log_failed(
                    "get_travel_matrix",
                    error=e,
                    fallback="haversine",
                )
            else:
                self.log_completed(
                    "get_travel_matrix",
                    pairs=len(matrix),
                    source="google",
                )
                return matrix

        # Fallback: calculate each pair using haversine
        for i, origin in enumerate(locations):
            for j, destination in enumerate(locations):
                if i != j:
                    matrix[(i, j)] = self.calculate_fallback_travel_time(
                        origin,
                        destination,
                    )

        self.log_completed("get_travel_matrix", pairs=len(matrix), source="fallback")
        return matrix

    async def _get_google_travel_matrix(
        self,
        locations: list[tuple[float, float]],
    ) -> dict[tuple[int, int], int]:
        """Get travel matrix from Google Maps Distance Matrix API.

        Args:
            locations: List of (latitude, longitude) tuples

        Returns:
            Dictionary mapping (from_index, to_index) to travel time in minutes
        """
        client = await self._get_client()

        # Format locations for API
        locations_str = "|".join(f"{lat},{lng}" for lat, lng in locations)

        params = {
            "origins": locations_str,
            "destinations": locations_str,
            "key": self.api_key or "",
            "mode": "driving",
        }

        response = await client.get(
            "https://maps.googleapis.com/maps/api/distancematrix/json",
            params=params,
        )
        response.raise_for_status()

        data = response.json()

        if data.get("status") != "OK":
            msg = f"Google Maps API error: {data.get('status')}"
            raise ValueError(msg)

        matrix: dict[tuple[int, int], int] = {}

        for i, row in enumerate(data["rows"]):
            for j, element in enumerate(row["elements"]):
                if i != j and element.get("status") == "OK":
                    duration_seconds = element["duration"]["value"]
                    matrix[(i, j)] = math.ceil(duration_seconds / 60)
                elif i != j:
                    # Use fallback for failed routes
                    matrix[(i, j)] = self.calculate_fallback_travel_time(
                        locations[i],
                        locations[j],
                    )

        return matrix

    def calculate_fallback_travel_time(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> int:
        """Calculate travel time using haversine formula with road factor.

        Uses straight-line distance with 1.4x factor for road distance,
        then calculates time based on average driving speed.

        Args:
            origin: (latitude, longitude) of origin
            destination: (latitude, longitude) of destination

        Returns:
            Estimated travel time in minutes

        Validates: Requirements 4.2, 4.5
        """
        # Calculate haversine distance
        lat1, lon1 = math.radians(origin[0]), math.radians(origin[1])
        lat2, lon2 = math.radians(destination[0]), math.radians(destination[1])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Straight-line distance in km
        straight_distance_km = EARTH_RADIUS_KM * c

        # Apply road factor
        road_distance_km = straight_distance_km * ROAD_FACTOR

        # Calculate time in minutes
        travel_time_hours = road_distance_km / AVERAGE_SPEED_KMH
        travel_time_minutes = travel_time_hours * 60

        # Return at least 1 minute, or default if calculation fails
        if travel_time_minutes < 1:
            return 1
        if travel_time_minutes > DEFAULT_TRAVEL_TIME_MINUTES * 10:
            return DEFAULT_TRAVEL_TIME_MINUTES

        return math.ceil(travel_time_minutes)
