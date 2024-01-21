"""Define services for HACS."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, callback, HomeAssistantError
from homeassistant.helpers.service import ServiceCall, SupportsResponse
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN
from .base import HacsBase
from .enums import HacsCategory

SERVICE_GET_REPOSITORES_FILTER_STATE_KEYS = ["downloaded", "new", "pending_update"]


@callback
def async_register_hacs_services(hass: HomeAssistant) -> None:
    """Register services for HACS."""
    hacs: HacsBase = hass.data[DOMAIN]
    if not hacs.configuration.experimental:
        return

    @callback
    def _get_repositories(call: ServiceCall) -> list[dict[str, any]]:
        """Get repositories."""
        if all(not call.data.get(key, False) for key in SERVICE_GET_REPOSITORES_FILTER_STATE_KEYS):
            raise HomeAssistantError(
                f"One of {", ".join(SERVICE_GET_REPOSITORES_FILTER_STATE_KEYS)} is required"
            )

        return {
            "repositories": [
                {
                    "id": repository.data.id,
                    "name": repository.display_name,
                    "repository": repository.data.full_name,
                    "category": repository.data.category,
                    "version_downloaded": repository.display_installed_version,
                    "version_available": repository.display_available_version,
                }
                for repository in hacs.repositories.list_all
                if (
                    (categories := call.data.get("categories")) is None
                    or repository.data.category in categories
                )
                and (not call.data.get("downloaded") or repository.data.installed)
                and (not call.data.get("new") or repository.data.new)
                and (not call.data.get("pending_update") or repository.pending_update)
            ],
        }

    hass.services.async_register(
        domain=DOMAIN,
        service="get_repositories",
        service_func=_get_repositories,
        schema=vol.Schema(
            {
                **{
                    vol.Exclusive(key, "state"): cv.boolean
                    for key in SERVICE_GET_REPOSITORES_FILTER_STATE_KEYS
                },
                vol.Optional("categories"): vol.All(cv.ensure_list, [vol.Coerce(HacsCategory)]),
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )


@callback
def async_unregister_hacs_services(hass: HomeAssistant) -> None:
    """Unregister services for HACS."""
    hacs: HacsBase = hass.data[DOMAIN]
    if not hacs.configuration.experimental:
        return
    hass.services.async_remove(domain=DOMAIN, service="get_repositories")
