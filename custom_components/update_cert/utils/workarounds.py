"""Workarounds."""

from homeassistant.core import HomeAssistant

DOMAIN_OVERRIDES = {
    # https://github.com/hacs/integration/issues/2465
    "custom-components/sensor.custom_aftership": "custom_aftership"
}


try:
    from homeassistant.components.http import StaticPathConfig

    async def async_register_static_path(
        hass: HomeAssistant,
        url_path: str,
        path: str,
        cache_headers: bool = True,
    ) -> None:
        """Register a static path with the HTTP component."""
        await hass.http.async_register_static_paths(
            [StaticPathConfig(url_path, path, cache_headers)]
        )
except ImportError:

    async def async_register_static_path(
        hass: HomeAssistant,
        url_path: str,
        path: str,
        cache_headers: bool = True,
    ) -> None:
        """Register a static path with the HTTP component.

        Legacy: Can be removed when min version is 2024.7
        https://developers.home-assistant.io/blog/2024/06/18/async_register_static_paths/
        """
        hass.http.register_static_path(url_path, path, cache_headers)
