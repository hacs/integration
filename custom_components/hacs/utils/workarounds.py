"""Workarounds."""

from aiogithubapi.models.git_tree import GitHubGitTreeEntryModel
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


class LegacyTreeFile:
    """Legacy TreeFile representation.

    This serves as a compatibility layer for code expecting
    the older TreeFile structure.
    """

    def __init__(self, model: GitHubGitTreeEntryModel, repository: str, ref: str):
        """Initialize."""
        self.model = model
        self.repository = repository
        self.ref = ref

        # Calculated attributes
        split_path = self.model.path.rsplit("/", 1)
        self.full_path = self.model.path
        self.is_directory = self.model.type == "tree"
        self.path = split_path[0] if "/" in self.model.path else ""
        self.filename = split_path[-1] if "/" in self.model.path else self.model.path
        self.url = self.model.url
        self.download_url = (
            f"https://raw.githubusercontent.com/{self.repository}/{self.ref}/{self.model.path}"
        )
