from __future__ import annotations

__version__ = "0.2.1"

import asyncio
import weakref

try:
    import zoneinfo
except ImportError:
    from backports import zoneinfo  # type: ignore[no-redef]


class CachedZoneInfo(zoneinfo.ZoneInfo):
    """Cache zone info objects."""

    _weak_cache: weakref.WeakValueDictionary[str, zoneinfo.ZoneInfo]

    @classmethod
    def get_cached_zone_info(cls, key: str) -> zoneinfo.ZoneInfo | None:
        """Get a cached zone info object."""
        return cls._weak_cache.get(key)


def get_time_zone(time_zone_str: str) -> zoneinfo.ZoneInfo:
    """Get a time zone object for the given time zone string."""
    return zoneinfo.ZoneInfo(time_zone_str)


async def async_get_time_zone(time_zone_str: str) -> zoneinfo.ZoneInfo:
    """Get a time zone object for the given time zone string."""
    return CachedZoneInfo.get_cached_zone_info(  # type: ignore[return-value]
        time_zone_str
    ) or await asyncio.get_running_loop().run_in_executor(
        None, get_time_zone, time_zone_str
    )


__all__ = ["async_get_time_zone"]
