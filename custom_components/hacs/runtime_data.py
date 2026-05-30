"""Runtime data attached to the HACS config entry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .utils.store import HACSStore


@dataclass
class HacsRuntimeData:
    """Runtime data for the HACS config entry."""

    store_cache: dict[str, HACSStore] = field(default_factory=dict)


HacsConfigEntry: TypeAlias = ConfigEntry[HacsRuntimeData]
