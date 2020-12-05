"""Provide info to system health."""
from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback
from aiogithubapi.common.const import BASE_API_URL

from .const import DOMAIN
from .base import HacsBase

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
    client: HacsBase = hass.data[DOMAIN]
    rate_limit = await client.github.get_rate_limit()

    return {
        "GitHub API": system_health.async_check_can_reach_url(
            hass, BASE_API_URL, GITHUB_STATUS
        ),
        "Github API Calls Remaining": rate_limit.get("remaining", "0"),
        "Installed Version": client.version,
        "Stage": client.stage,
        "Available Repositories": len(client.repositories),
        "Installed Repositories": len(
            [repo for repo in client.repositories if repo.data.installed]
        ),
    }
