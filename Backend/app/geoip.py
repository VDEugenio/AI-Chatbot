"""
Coarse IP-to-location lookup for notification messages.

Uses ip-api.com's free tier (45 req/min, no key required, HTTP only) — fine
for backend-to-backend calls. Results are cached in-process via lru_cache to
avoid repeated lookups for the same visitor and to stay well under the rate
limit. On any failure we return `_UNKNOWN` so the caller can still send a
notification, just without geo info.
"""

from __future__ import annotations

import ipaddress
import logging
from functools import lru_cache
from typing import NamedTuple

import httpx

logger = logging.getLogger(__name__)


class GeoInfo(NamedTuple):
    label: str             # human-readable, e.g. "New York, NY, US"
    city: str | None
    region: str | None
    country: str | None
    country_code: str | None
    isp: str | None


_UNKNOWN = GeoInfo(
    label="Unknown location",
    city=None,
    region=None,
    country=None,
    country_code=None,
    isp=None,
)
_LOCAL = GeoInfo(
    label="local / private network",
    city=None,
    region=None,
    country=None,
    country_code=None,
    isp=None,
)


def _is_local_or_private(ip: str) -> bool:
    """True for loopback, link-local, or RFC1918 addresses."""
    if not ip or ip in ("unknown", "localhost"):
        return True
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return addr.is_private or addr.is_loopback or addr.is_link_local


@lru_cache(maxsize=1024)
def lookup(ip: str) -> GeoInfo:
    """Cached IP lookup. Synchronous on purpose — call via asyncio.to_thread."""
    if _is_local_or_private(ip):
        return _LOCAL
    try:
        resp = httpx.get(
            f"http://ip-api.com/json/{ip}",
            params={"fields": "status,city,regionName,country,countryCode,isp"},
            timeout=2.5,
        )
        data = resp.json()
        if data.get("status") != "success":
            return _UNKNOWN

        city = data.get("city") or None
        region = data.get("regionName") or None
        country = data.get("country") or None
        country_code = data.get("countryCode") or None
        isp = data.get("isp") or None

        # Build a compact label like "Brooklyn, NY, US" or "Tokyo, JP".
        parts: list[str] = []
        if city:
            parts.append(city)
        if region and region != city:
            parts.append(region)
        if country_code:
            parts.append(country_code)
        label = ", ".join(parts) if parts else (country or "Unknown location")

        return GeoInfo(
            label=label,
            city=city,
            region=region,
            country=country,
            country_code=country_code,
            isp=isp,
        )
    except Exception as exc:
        logger.warning("GeoIP lookup failed for %s: %s", ip, exc)
        return _UNKNOWN
