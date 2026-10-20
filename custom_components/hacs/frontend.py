"""Starting setup task: Frontend."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.frontend import add_extra_js_url

from .const import DOMAIN, URL_BASE
from .utils.workarounds import async_register_static_path

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .base import HacsBase

ICONSET_REGISTERED = f"{DOMAIN}_iconset_registered"


async def async_register_frontend(hass: HomeAssistant, hacs: HacsBase) -> None:
    """Register the frontend."""

    # Custom iconset, static paths can't be registered again when the entry reloads
    iconset_url = f"{URL_BASE}/iconset.js"
    if not hass.data.get(ICONSET_REGISTERED):
        await async_register_static_path(
            hass, iconset_url, str(hacs.integration_dir / "iconset.js")
        )
        add_extra_js_url(hass, iconset_url)
        hass.data[ICONSET_REGISTERED] = True

    # Setup plugin endpoint if needed
    await hacs.async_setup_frontend_endpoint_plugin()
