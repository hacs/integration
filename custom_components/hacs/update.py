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

    @property
    def supported_features(self) -> int | None:
        """Return the supported features of the entity."""
        features = 16
        if self.repository.can_download:
            features = features | 1
        return features

    @property
    def name(self) -> str | None:
        """Return the name."""
        return f"{self.repository.display_name} update"

    @property
    def latest_version(self) -> str:
        """Return latest version of the entity."""
        return self.repository.display_available_version

    @property
    def release_url(self) -> str:
        """Return the URL of the release page."""
        if self.repository.display_version_or_commit == "commit":
            return f"https://github.com/{self.repository.data.full_name}"
        return f"https://github.com/{self.repository.data.full_name}/releases/{self.latest_version}"

    @property
    def installed_version(self) -> str:
        """Return downloaded version of the entity."""
        return self.repository.display_installed_version

    @property
    def release_summary(self) -> str | None:
        """Return the release summary."""
        if not self.repository.can_download:
            return f"<ha-alert alert-type='warning'>Requires Home Assistant {self.repository.data.homeassistant}</ha-alert>"
        if self.repository.pending_restart:
            return "<ha-alert alert-type='error'>Restart of Home Assistant required</ha-alert>"
        return None

    @property
    def entity_picture(self) -> str | None:
        """Return the entity picture to use in the frontend."""
        if (
            self.repository.data.category != HacsCategory.INTEGRATION
            or self.repository.data.domain is None
        ):
            return None

        return f"https://brands.home-assistant.io/_/{self.repository.data.domain}/icon.png"

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install an update."""
        if self.repository.display_version_or_commit == "version":
            self.repository.data.selected_tag = self.latest_version
            await self.repository.update_repository(force=True)
        await self.repository.async_install()

    async def async_release_notes(self) -> str | None:
        """Return the release notes."""
        if self.repository.pending_restart or not self.repository.can_download:
            return None

        release_notes = ""
        if len(self.repository.releases.objects) > 0:
            release = self.repository.releases.objects[0]
            release_notes += release.body

        if self.repository.pending_update:
            if self.repository.data.category == HacsCategory.INTEGRATION:
                release_notes += (
                    "\n\n<ha-alert alert-type='warning'>You need to restart"
                    " Home Assistant manually after updating.</ha-alert>\n\n"
                )
            if self.repository.data.category == HacsCategory.PLUGIN:
                release_notes += (
                    "\n\n<ha-alert alert-type='warning'>You need to manually"
                    " clear the frontend cache after updating.</ha-alert>\n\n"
                )

        return release_notes.replace("\n#", "\n\n#")
