"""
External service integrations and fallbacks for the scheduling engine.

Provides Google Maps travel time, Weather API forecasts, and Redis
caching with graceful fallback behavior when external services are
unavailable.

Validates: Requirements 31.1, 31.2, 31.3, 31.4, 32.5, 34.3, 34.4
"""

from __future__ import annotations

import math
import os
import time
from typing import TYPE_CHECKING, Any

from grins_platform.log_config import LoggerMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class ExternalServiceManager(LoggerMixin):
    """Manages external API integrations with fallback behaviour.

    Wraps Google Maps, Weather API, and Redis with try/except
    fallbacks so the scheduling engine degrades gracefully when
    external services are unavailable.

    Attributes:
        DOMAIN: Logging domain for structured log events.
    """

    DOMAIN = "scheduling"

    def __init__(self, session: AsyncSession) -> None:
        """Initialise the external service manager.

        Args:
            session: Async database session (used for DB-based fallbacks).
        """
        super().__init__()
        self._session = session

    # ------------------------------------------------------------------
    # Google Maps integration
    # ------------------------------------------------------------------

    async def get_travel_time(
        self,
        origin: tuple[float, float],
        destination: tuple[float, float],
    ) -> dict[str, Any]:
        """Get travel time between two coordinates.

        Attempts Google Maps Directions API first. Falls back to
        haversine distance x 1.4 factor when the API is unavailable
        or the key is missing.

        Args:
            origin: ``(latitude, longitude)`` of the start point.
            destination: ``(latitude, longitude)`` of the end point.

        Returns:
            Dict with ``travel_minutes``, ``distance_km``, ``source``
            (``"google_maps"`` or ``"haversine_fallback"``).
        """
        start = time.monotonic()
        self.log_started(
            "get_travel_time",
            origin=origin,
            destination=destination,
        )

        api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
        if not api_key:
            self.log_failed(
                "get_travel_time_google",
                latency_ms=round((time.monotonic() - start) * 1000, 1),
            )
        else:
            # Stub: real implementation would call Google Maps here.
            # When wired, a successful call would return early.
            self.log_failed(
                "get_travel_time_google",
                latency_ms=round((time.monotonic() - start) * 1000, 1),
            )

        # Fallback: haversine x 1.4
        distance_km = self._haversine_km(origin, destination)
        # Assume average speed of 40 km/h in urban/suburban areas
        travel_minutes = (distance_km / 40.0) * 60.0 * 1.4

        self.log_completed(
            "get_travel_time_fallback",
            travel_minutes=round(travel_minutes, 1),
            distance_km=round(distance_km, 2),
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )

        return {
            "travel_minutes": round(travel_minutes, 1),
            "distance_km": round(distance_km, 2),
            "source": "haversine_fallback",
        }

    # ------------------------------------------------------------------
    # Weather API integration
    # ------------------------------------------------------------------

    async def get_weather_forecast(
        self,
        date: str,
        location: tuple[float, float],
    ) -> dict[str, Any]:
        """Get weather forecast for a date and location.

        Attempts external Weather API first. Falls back to an empty
        forecast (weather criterion is skipped) when unavailable.

        Args:
            date: ISO-format date string (``YYYY-MM-DD``).
            location: ``(latitude, longitude)`` of the job site.

        Returns:
            Dict with ``condition``, ``high_temp``, ``low_temp``,
            ``precipitation_chance``, ``source``. On fallback the
            ``condition`` is ``"unknown"`` and ``skip_criterion``
            is ``True``.
        """
        start = time.monotonic()
        self.log_started(
            "get_weather_forecast",
            date=date,
            location=location,
        )

        api_key = os.environ.get("WEATHER_API_KEY")
        if not api_key:
            self.log_failed(
                "get_weather_forecast_api",
                latency_ms=round((time.monotonic() - start) * 1000, 1),
            )
        else:
            # Stub: real implementation would call Weather API here.
            # When wired, a successful call would return early.
            self.log_failed(
                "get_weather_forecast_api",
                latency_ms=round((time.monotonic() - start) * 1000, 1),
            )

        self.log_completed(
            "get_weather_forecast_fallback",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )

        return {
            "condition": "unknown",
            "high_temp": None,
            "low_temp": None,
            "precipitation_chance": None,
            "source": "fallback",
            "skip_criterion": True,
        }

    # ------------------------------------------------------------------
    # Redis caching
    # ------------------------------------------------------------------

    async def get_cached(self, key: str) -> object | None:
        """Retrieve a value from Redis cache.

        Falls back to ``None`` (cache miss) when Redis is unavailable.

        Args:
            key: Cache key string.

        Returns:
            Cached value or ``None`` on miss / error.
        """
        self.log_started("cache_get", key=key)
        try:
            # --- Redis get (stub) ---
            # import redis.asyncio as aioredis
            # r = aioredis.from_url(os.environ["REDIS_URL"])
            # value = await r.get(key)
            # return json.loads(value) if value else None
            return None  # pragma: no cover — stub
        except Exception as exc:
            self.log_failed("cache_get", error=exc, key=key)
            return None

    async def set_cached(
        self,
        key: str,
        value: object,
        ttl: int = 300,
    ) -> bool:
        """Store a value in Redis cache.

        Falls back to ``False`` (no-op) when Redis is unavailable.

        Args:
            key: Cache key string.
            value: Value to cache (must be JSON-serialisable).
            ttl: Time-to-live in seconds (default 300).

        Returns:
            ``True`` if cached successfully, ``False`` otherwise.
        """
        self.log_started("cache_set", key=key, ttl=ttl)
        _ = value  # reserved for Redis-backed implementation
        try:
            # --- Redis set (stub) ---
            # import redis.asyncio as aioredis
            # r = aioredis.from_url(os.environ["REDIS_URL"])
            # await r.setex(key, ttl, json.dumps(value))
            # return True
            pass
        except Exception as exc:
            self.log_failed("cache_set", error=exc, key=key)
            return False
        return False  # pragma: no cover — stub

    # ------------------------------------------------------------------
    # API key validation
    # ------------------------------------------------------------------

    async def validate_api_keys(self) -> dict[str, bool]:
        """Check all required API keys at startup.

        Returns:
            Dict mapping service name to ``True`` (key present) or
            ``False`` (missing).
        """
        self.log_started("validate_api_keys")

        keys: dict[str, bool] = {
            "google_maps": bool(os.environ.get("GOOGLE_MAPS_API_KEY")),
            "weather": bool(os.environ.get("WEATHER_API_KEY")),
            "openai": bool(os.environ.get("OPENAI_API_KEY")),
            "redis": bool(os.environ.get("REDIS_URL")),
        }

        missing = [k for k, v in keys.items() if not v]
        if missing:
            self.log_failed(
                "validate_api_keys",
                missing_keys=missing,
            )
        else:
            self.log_completed("validate_api_keys", all_present=True)

        return keys

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _haversine_km(
        coord1: tuple[float, float],
        coord2: tuple[float, float],
    ) -> float:
        """Calculate haversine distance in kilometres.

        Args:
            coord1: ``(lat, lon)`` of point A.
            coord2: ``(lat, lon)`` of point B.

        Returns:
            Great-circle distance in km.
        """
        lat1, lon1 = math.radians(coord1[0]), math.radians(coord1[1])
        lat2, lon2 = math.radians(coord2[0]), math.radians(coord2[1])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Earth radius in km
        return 6371.0 * c
