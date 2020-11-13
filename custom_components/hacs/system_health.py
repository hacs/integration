"""Provide info to system health."""
from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback
from aiogithubapi.common.const import BASE_API_URL

from .const import DOMAIN, NAME_LONG

GITHUB_STATUS = "https://www.githubstatus.com/"


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.domain = "Home Assistant Community Store"
    register.async_register_info(system_health_info, "/hacs")


async def system_health_info(hass):
    """Get info for the info page."""
    client = hass.data[DOMAIN]

    return {
        "GitHub API": system_health.async_check_can_reach_url(
            hass, BASE_API_URL, GITHUB_STATUS
        ),
        "Installed version": client.version,
        "Available repositories": len(client.repositories),
        "Installed repositories": len(
            [repo for repo in client.repositories if repo.data.installed]
        ),
    }
