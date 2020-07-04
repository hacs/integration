"""Setup functions for HACS."""
# pylint: disable=bad-continuation
import os

from hacs_frontend.version import VERSION as FE_VERSION


from custom_components.hacs.api.register import async_setup_hacs_websockt_api

from custom_components.hacs.hacs import get_hacs
from custom_components.hacs.helpers.functions.information import get_frontend_version


def setup_extra_stores():
    """Set up extra stores in HACS if enabled in Home Assistant."""
    hacs = get_hacs()
    if "python_script" in hacs.hass.config.components:
        if "python_script" not in hacs.common.categories:
            hacs.common.categories.append("python_script")

    if hacs.hass.services.services.get("frontend", {}).get("reload_themes") is not None:
        if "theme" not in hacs.common.categories:
            hacs.common.categories.append("theme")


async def setup_frontend():
    """Configure the HACS frontend elements."""
    from .http import HacsFrontend

    hacs = get_hacs()

    hacs.hass.http.register_view(HacsFrontend())
    hacs.frontend.version_running = FE_VERSION
    hacs.frontend.version_expected = await hacs.hass.async_add_executor_job(
        get_frontend_version
    )

    # Add to sidepanel
    custom_panel_config = {
        "name": "hacs-frontend",
        "embed_iframe": False,
        "trust_external": False,
        "js_url": f"/hacsfiles/frontend-{hacs.frontend.version_running}.js",
    }

    config = {}
    config["_panel_custom"] = custom_panel_config

    hacs.hass.components.frontend.async_register_built_in_panel(
        component_name="custom",
        sidebar_title=hacs.configuration.sidepanel_title,
        sidebar_icon=hacs.configuration.sidepanel_icon,
        frontend_url_path="hacs",
        config=config,
        require_admin=True,
    )

    if "frontend_extra_module_url" not in hacs.hass.data:
        hacs.hass.data["frontend_extra_module_url"] = set()
    hacs.hass.data["frontend_extra_module_url"].add("/hacsfiles/iconset.js")

    await async_setup_hacs_websockt_api()
