"""Setup functions for HACS."""
# pylint: disable=bad-continuation
from hacs_frontend.version import VERSION as FE_VERSION
from homeassistant.helpers import discovery

from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.const import VERSION, DOMAIN
from custom_components.hacs.globals import get_hacs
from custom_components.hacs.helpers.information import get_repository
from custom_components.hacs.helpers.register_repository import register_repository


async def load_hacs_repository():
    """Load HACS repositroy."""
    hacs = get_hacs()

    try:
        repository = hacs.get_by_name("hacs/integration")
        if repository is None:
            await register_repository("hacs/integration", "integration")
            repository = hacs.get_by_name("hacs/integration")
        if repository is None:
            raise HacsException("Unknown error")
        repository.status.installed = True
        repository.versions.installed = VERSION
        repository.status.new = False
        hacs.repo = repository.repository_object
        hacs.data_repo = await get_repository(
            hacs.session, hacs.configuration.token, "hacs/default"
        )
    except HacsException as exception:
        if "403" in f"{exception}":
            hacs.logger.critical("GitHub API is ratelimited, or the token is wrong.")
        else:
            hacs.logger.critical(f"[{exception}] - Could not load HACS!")
        return False
    return True


def setup_extra_stores():
    """Set up extra stores in HACS if enabled in Home Assistant."""
    hacs = get_hacs()
    if "python_script" in hacs.hass.config.components:
        if "python_script" not in hacs.common.categories:
            hacs.common.categories.append("python_script")

    if hacs.hass.services.services.get("frontend", {}).get("reload_themes") is not None:
        if "theme" not in hacs.common.categories:
            hacs.common.categories.append("theme")


def add_sensor():
    """Add sensor."""
    hacs = get_hacs()

    try:
        if hacs.configuration.config_type == "yaml":
            hacs.hass.async_create_task(
                discovery.async_load_platform(
                    hacs.hass, "sensor", DOMAIN, {}, hacs.configuration.config
                )
            )
        else:
            hacs.hass.async_add_job(
                hacs.hass.config_entries.async_forward_entry_setup(
                    hacs.configuration.config_entry, "sensor"
                )
            )
    except ValueError:
        pass


async def setup_frontend():
    """Configure the HACS frontend elements."""
    from .http import HacsFrontend, HacsPluginViewLegacy
    from .ws_api_handlers import setup_ws_api

    hacs = get_hacs()

    hacs.hass.http.register_view(HacsFrontend())
    hacs.frontend.version_running = FE_VERSION

    # Legacy views, remove with 2.0
    hacs.hass.http.register_view(HacsPluginViewLegacy())

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

    await setup_ws_api(hacs.hass)
