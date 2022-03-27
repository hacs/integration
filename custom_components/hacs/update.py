"""Update entities for HACS."""
from __future__ import annotations

from typing import Any

from homeassistant.components.update import UpdateEntity

from .base import HacsBase
from .const import DOMAIN
from .entity import HacsRepositoryEntity
from .enums import HacsCategory


async def async_setup_entry(hass, _config_entry, async_add_devices):
    """Setup update platform."""
    hacs: HacsBase = hass.data.get(DOMAIN)
    async_add_devices(
        HacsRepositoryUpdateEntity(hacs=hacs, repository=repository)
        for repository in hacs.repositories.list_downloaded
    )


class HacsRepositoryUpdateEntity(HacsRepositoryEntity, UpdateEntity):
    """Update entities for repositories downloaded with HACS."""

    _attr_supported_features = 1

    @property
    def name(self) -> str | None:
        return f"{self.repository.display_name} update"

    @property
    def latest_version(self) -> str:
        """Return latest version of the entity."""
        return self.repository.display_available_version

    @property
    def release_summary(self) -> str | None:
        """Return the release summary."""
        if self.repository.pending_restart:
            return "🔴 Restart of Home Assistant required 🔴 "
        if self.repository.pending_update:
            if self.repository.data.category == HacsCategory.INTEGRATION:
                return "🟡 You need to restart Home Assistant manually after updating."
            if self.repository.data.category == HacsCategory.PLUGIN:
                return "🟡 You manually clear the frontend cache after updating."
        return None

    @property
    def release_url(self) -> str:
        """Return the URL of the release page."""
        if self.repository.display_version_or_commit == "commit":
            return f"https://github.com/{self.repository.data.full_name}"
        return f"https://github.com/{self.repository.data.full_name}/releases/{self.latest_version}"

    @property
    def current_version(self) -> str:
        """Return latest version of the entity."""
        return self.repository.display_installed_version

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install an update."""
        if self.repository.display_version_or_commit == "version":
            self.repository.data.selected_tag = self.latest_version
            await self.repository.update_repository(force=True)
        await self.repository.async_install()
