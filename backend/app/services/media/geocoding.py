"""Lightweight geocoding using OpenStreetMap Nominatim.

Turns place labels / addresses extracted from reels, posts or links into
concrete (latitude, longitude) coordinates so LOCATION triggers can evaluate
real-world proximity (§19).
"""

from __future__ import annotations

import asyncio
from typing import Any
import httpx

from app.utils.logging import get_logger

logger = get_logger(__name__)

_USER_AGENT = "EchoApp/1.0 (contact: demo@echo.app)"
_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_CACHE: dict[str, tuple[float, float] | None] = {}
_LOCK = asyncio.Lock()


async def geocode(query: str | None) -> tuple[float, float] | None:
    """Resolve a place name or address into (latitude, longitude).

    Returns None if the query is empty or cannot be resolved.
    """
    if not query or not query.strip():
        return None

    cleaned = query.strip()
    if cleaned in _CACHE:
        return _CACHE[cleaned]

    async with _LOCK:
        if cleaned in _CACHE:
            return _CACHE[cleaned]

        try:
            async with httpx.AsyncClient(
                timeout=5.0,
                headers={"User-Agent": _USER_AGENT},
            ) as client:
                response = await client.get(
                    _NOMINATIM_URL,
                    params={"q": cleaned, "format": "json", "limit": 1},
                )
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list) and len(data) > 0:
                        item: dict[str, Any] = data[0]
                        lat = float(item["lat"])
                        lon = float(item["lon"])
                        _CACHE[cleaned] = (lat, lon)
                        logger.info("geocoding.resolved", query=cleaned, lat=lat, lon=lon)
                        return (lat, lon)
        except Exception as exc:
            logger.warning("geocoding.failed", query=cleaned, error=str(exc))

        _CACHE[cleaned] = None
        return None


def set_cached_location(query: str, lat: float, lon: float) -> None:
    """Seed or override a geocoded location in cache (useful for tests/demos)."""
    _CACHE[query.strip()] = (lat, lon)
