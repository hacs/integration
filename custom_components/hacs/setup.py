"""Setup functions for HACS."""
# pylint: disable=bad-continuation
from aiogithubapi import AIOGitHubAuthentication, AIOGitHubException, AIOGitHubRatelimit

from homeassistant.helpers import discovery

from .const import VERSION, DOMAIN
from .http import HacsPluginView, HacsFrontend
from .ws_api_handlers import setup_ws_api


async def load_hacs_repository(hacs):
    """Load HACS repositroy."""
    try:
        repository = hacs().get_by_name("hacs/integration")
        if repository is None:
            await hacs().register_repository("hacs/integration", "integration")
            repository = hacs().get_by_name("hacs/integration")
        if repository is None:
            raise AIOGitHubException("Unknown error")
        repository.status.installed = True
        repository.versions.installed = VERSION
        repository.status.new = False
        hacs.repo = repository.repository_object
        hacs.data_repo = await hacs().github.get_repo("hacs/default")
    except (
        AIOGitHubException,
        AIOGitHubRatelimit,
        AIOGitHubAuthentication,
    ) as exception:
        hacs.logger.critical(f"[{exception}] - Could not load HACS!")
        return False
    return True


def add_sensor(hacs):
    """Add sensor."""
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


async def setup_frontend(hacs):
    """Configure the HACS frontend elements."""
    hacs.hass.http.register_view(HacsPluginView())

    # Add to sidepanel
    hacs.hass.http.register_view(HacsFrontend())
    custom_panel_config = {
        "name": "hacs-frontend",
        "embed_iframe": False,
        "trust_external": False,
        "js_url": f"/hacs_frontend/main.js?v={hacs.version}",
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
    await setup_ws_api(hacs.hass)
