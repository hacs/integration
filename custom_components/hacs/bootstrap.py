"""Bootstrap HACS."""

from .base import HacsBase


async def bootstrap_hacs(hass) -> None:
    """Bootstrap HACS."""
    hacs = HacsBase()
    hacs.hass = hass
