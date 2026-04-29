"""
External service integrations and fallbacks for AI scheduling.

Provides Google Maps, Weather API, and Redis integrations with
graceful fallbacks for each.

Validates: Requirements 31.1, 31.2, 31.3, 31.4, 32.5, 34.3, 34.4
"""

from __future__ import annotations

import json
import math
import os
import time
import urllib.parse
from typing import Any

from grins_platform.log_config import LoggerMixin

# Haversine fallback factor (drive time ~= 1.4x straight-line travel time)
_HAVERSINE_FACTOR = 1.4
_AVG_SPEED_KMH = 40.0  # average urban speed


def _haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate straight-line distance in km using the haversine formula."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


class ExternalServicesClient(LoggerMixin):
    """Client for external service integrations with fallbacks.

    Wraps Google Maps, Weather API, and Redis with graceful degradation
    when services are unavailable.

    Attributes:
        DOMAIN: Logging domain identifier.
    """

    DOMAIN = "scheduling"

    def __init__(self) -> None:
        """Initialise the external services client."""
        super().__init__()
        self._maps_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self._weather_key = os.getenv("WEATHER_API_KEY")
        self._redis_url = os.getenv("REDIS_URL")

        if not self._maps_key:
            self.logger.warning(
                "scheduling.external.google_maps_key_missing",
                message="GOOGLE_MAPS_API_KEY not set -- using haversine fallback",
            )
        if not self._weather_key:
            self.logger.warning(
                "scheduling.external.weather_key_missing",
                message=(
                    "WEATHER_API_KEY not set -- weather criterion will be skipped"
                ),
            )

    async def get_travel_time_minutes(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        *,
        with_traffic: bool = False,
    ) -> float:
        """Get travel time in minutes between two coordinates.

        Uses Google Maps when available; falls back to haversine x 1.4.

        Args:
            origin_lat: Origin latitude.
            origin_lon: Origin longitude.
            dest_lat: Destination latitude.
            dest_lon: Destination longitude.
            with_traffic: Whether to include real-time traffic.

        Returns:
            Estimated travel time in minutes.
        """
        start = time.monotonic()

        if self._maps_key:
            try:
                result = await self._google_maps_travel_time(
                    origin_lat,
                    origin_lon,
                    dest_lat,
                    dest_lon,
                    with_traffic=with_traffic,
                )
                latency_ms = (time.monotonic() - start) * 1000
                self.logger.info(
                    "scheduling.external.google_maps_travel_time",
                    latency_ms=round(latency_ms, 1),
                    with_traffic=with_traffic,
                )
            except Exception as exc:
                self.log_failed(
                    "google_maps_travel_time",
                    error=exc,
                )
            else:
                return result

        return self._haversine_travel_time(
            origin_lat,
            origin_lon,
            dest_lat,
            dest_lon,
        )

    async def get_weather_forecast(
        self,
        lat: float,
        lon: float,
        days: int = 7,
    ) -> list[dict[str, Any]] | None:
        """Get weather forecast for a location.

        Returns None if weather API is unavailable (criterion skipped).

        Args:
            lat: Latitude.
            lon: Longitude.
            days: Number of forecast days (max 7).

        Returns:
            List of daily forecast dicts, or None if unavailable.
        """
        if not self._weather_key:
            return None

        start = time.monotonic()
        try:
            result = await self._fetch_weather(lat, lon, days)
            latency_ms = (time.monotonic() - start) * 1000
            self.logger.info(
                "scheduling.external.weather_forecast_fetched",
                latency_ms=round(latency_ms, 1),
                days=days,
            )
        except Exception as exc:
            self.log_failed("get_weather_forecast", error=exc)
            return None
        else:
            return result

    async def cache_get(
        self,
        key: str,
    ) -> object | None:
        """Get a value from Redis cache.

        Falls back to None (cache miss) if Redis is unavailable.

        Args:
            key: Cache key.

        Returns:
            Cached value or None.
        """
        if not self._redis_url:
            return None

        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]  # noqa: PLC0415

            client = aioredis.from_url(self._redis_url)
            raw = await client.get(key)
            await client.aclose()
            if raw is None:
                return None
            return json.loads(raw)  # type: ignore[no-any-return]
        except Exception as exc:
            self.log_failed("cache_get", error=exc, key=key)
            return None

    async def cache_set(
        self,
        key: str,
        value: object,
        ttl_seconds: int = 300,
    ) -> bool:
        """Set a value in Redis cache.

        Returns False if Redis is unavailable (non-fatal).

        Args:
            key: Cache key.
            value: Value to cache (must be JSON-serialisable).
            ttl_seconds: TTL in seconds.

        Returns:
            True if cached successfully, False otherwise.
        """
        if not self._redis_url:
            return False

        try:
            import redis.asyncio as aioredis  # type: ignore[import-untyped]  # noqa: PLC0415

            client = aioredis.from_url(self._redis_url)
            await client.setex(key, ttl_seconds, json.dumps(value))
            await client.aclose()
        except Exception as exc:
            self.log_failed("cache_set", error=exc, key=key)
            return False
        else:
            return True

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _google_maps_travel_time(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        *,
        with_traffic: bool = False,
    ) -> float:
        """Call Google Maps Distance Matrix API.

        Args:
            origin_lat: Origin latitude.
            origin_lon: Origin longitude.
            dest_lat: Destination latitude.
            dest_lon: Destination longitude.
            with_traffic: Whether to include traffic.

        Returns:
            Travel time in minutes.
        """
        import httpx  # type: ignore[import-untyped]  # noqa: PLC0415

        origin = f"{origin_lat},{origin_lon}"
        destination = f"{dest_lat},{dest_lon}"
        params: dict[str, str] = {
            "origins": origin,
            "destinations": destination,
            "key": self._maps_key or "",
            "units": "metric",
        }
        if with_traffic:
            params["departure_time"] = "now"

        url = (
            "https://maps.googleapis.com/maps/api/distancematrix/json?"
            + urllib.parse.urlencode(params)
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        element = data["rows"][0]["elements"][0]
        if element["status"] != "OK":
            msg = f"Google Maps API returned status: {element['status']}"
            raise RuntimeError(msg)

        duration_key = "duration_in_traffic" if with_traffic else "duration"
        seconds: float = element[duration_key]["value"]
        return seconds / 60.0

    async def _fetch_weather(
        self,
        lat: float,
        lon: float,
        days: int,
    ) -> list[dict[str, Any]]:
        """Fetch weather forecast from OpenWeatherMap.

        Args:
            lat: Latitude.
            lon: Longitude.
            days: Number of forecast days.

        Returns:
            List of daily forecast dicts.
        """
        import httpx  # type: ignore[import-untyped]  # noqa: PLC0415

        url = "https://api.openweathermap.org/data/2.5/forecast/daily"
        params: dict[str, str | int | float] = {
            "lat": lat,
            "lon": lon,
            "cnt": min(days, 7),
            "appid": self._weather_key or "",
            "units": "imperial",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

        forecasts: list[dict[str, Any]] = []
        for item in data.get("list", []):
            weather = item.get("weather", [{}])[0]
            forecasts.append(
                {
                    "date": item.get("dt"),
                    "temp_high": item.get("temp", {}).get("max"),
                    "temp_low": item.get("temp", {}).get("min"),
                    "description": weather.get("description", ""),
                    "main": weather.get("main", ""),
                    "precipitation_mm": item.get("rain", 0),
                    "snow_mm": item.get("snow", 0),
                    "is_severe": weather.get("main", "")
                    in ("Thunderstorm", "Snow", "Extreme"),
                }
            )
        return forecasts

    @staticmethod
    def _haversine_travel_time(
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        """Estimate travel time using haversine distance x 1.4 factor.

        Args:
            lat1: Origin latitude.
            lon1: Origin longitude.
            lat2: Destination latitude.
            lon2: Destination longitude.

        Returns:
            Estimated travel time in minutes.
        """
        dist_km = _haversine_km(lat1, lon1, lat2, lon2)
        drive_km = dist_km * _HAVERSINE_FACTOR
        hours = drive_km / _AVG_SPEED_KMH
        return hours * 60.0
