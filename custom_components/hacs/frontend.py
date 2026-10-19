"""Starting setup task: Frontend."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL, add_extra_js_url

from .const import URL_BASE
from .utils.workarounds import async_register_static_path

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .base import HacsBase


async def async_register_frontend(hass: HomeAssistant, hacs: HacsBase) -> None:
    """Register the frontend."""

    # Custom iconset, static paths can't be registered again when the entry reloads
    iconset_url = f"{URL_BASE}/iconset.js"
    if iconset_url not in hass.data[DATA_EXTRA_MODULE_URL].urls:
        await async_register_static_path(
            hass, iconset_url, str(hacs.integration_dir / "iconset.js")
        )
        add_extra_js_url(hass, iconset_url)

    # Setup plugin endpoint if needed
    await hacs.async_setup_frontend_endpoint_plugin()
