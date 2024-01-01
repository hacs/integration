"""Update entities for HACS."""
from __future__ import annotations

from typing import Any

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.core import HomeAssistantError, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .base import HacsBase
from .const import DOMAIN
from .entity import HacsRepositoryEntity
from .enums import HacsCategory, HacsDispatchEvent
from .exceptions import HacsException
from .repositories.base import HacsManifest


async def async_setup_entry(hass, _config_entry, async_add_devices):
    """Setup update platform."""
    hacs: HacsBase = hass.data.get(DOMAIN)
    async_add_devices(
        HacsRepositoryUpdateEntity(hacs=hacs, repository=repository)
        for repository in hacs.repositories.list_downloaded
    )


class HacsRepositoryUpdateEntity(HacsRepositoryEntity, UpdateEntity):
    """Update entities for repositories downloaded with HACS."""

    _attr_supported_features = (
        UpdateEntityFeature.INSTALL
        | UpdateEntityFeature.SPECIFIC_VERSION
        | UpdateEntityFeature.PROGRESS
        | UpdateEntityFeature.RELEASE_NOTES
    )

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
            return f"<ha-alert alert-type='warning'>Requires Home Assistant {self.repository.repository_manifest.homeassistant}</ha-alert>"
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

    async def _ensure_capabilities(self, version: str | None, **kwargs: Any) -> None:
        """Ensure that the entity has capabilities."""
        target_manifest: HacsManifest | None = None
        if version is None:
            if not self.repository.can_download:
                raise HomeAssistantError(
                    f"This {self.repository.data.category.value} is not available for download."
                )
            return

        if version == self.repository.data.last_version:
            target_manifest = self.repository.repository_manifest
        else:
            target_manifest = await self.repository.get_hacs_json(version=version)

        if target_manifest is None:
            raise HomeAssistantError(
                f"The version {version} for this {self.repository.data.category.value} can not be used with HACS."
            )

        if (
            target_manifest.homeassistant is not None
            and self.hacs.core.ha_version < target_manifest.homeassistant
        ):
            raise HomeAssistantError(
                f"This version requires Home Assistant {target_manifest.homeassistant} or newer."
            )
        if target_manifest.hacs is not None and self.hacs.version < target_manifest.hacs:
            raise HomeAssistantError(f"This version requires HACS {target_manifest.hacs} or newer.")

    async def async_install(self, version: str | None, backup: bool, **kwargs: Any) -> None:
        """Install an update."""
        await self._ensure_capabilities(version)
        self.repository.logger.info("Starting update, %s", version)
        if self.repository.display_version_or_commit == "version":
            self._update_in_progress(progress=10)
            if not version:
                await self.repository.update_repository(force=True)
            else:
                self.repository.ref = version
            self.repository.data.selected_tag = version
            self.repository.force_branch = version is not None
            self._update_in_progress(progress=20)

        try:
            await self.repository.async_install(version=version)
        except HacsException as exception:
            raise HomeAssistantError(
                f"Downloading {self.repository.data.full_name} with version {version or self.repository.data.last_version or self.repository.data.last_commit} failed with ({exception})"
            ) from exception
        finally:
            self.repository.data.selected_tag = None
            self.repository.force_branch = False
            self._update_in_progress(progress=False)

    async def async_release_notes(self) -> str | None:
        """Return the release notes."""
        if self.repository.pending_restart or not self.repository.can_download:
            return None

        if self.latest_version not in self.repository.data.published_tags:
            releases = await self.repository.get_releases(
                prerelease=self.repository.data.show_beta,
                returnlimit=self.hacs.configuration.release_limit,
            )
            if releases:
                self.repository.data.releases = True
                self.repository.releases.objects = releases
                self.repository.data.published_tags = [x.tag_name for x in releases]
                self.repository.data.last_version = next(iter(self.repository.data.published_tags))

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

    async def async_added_to_hass(self) -> None:
        """Register for status events."""
        await super().async_added_to_hass()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                HacsDispatchEvent.REPOSITORY_DOWNLOAD_PROGRESS,
                self._update_download_progress,
            )
        )

    @callback
    def _update_download_progress(self, data: dict) -> None:
        """Update the download progress."""
        if data["repository"] != self.repository.data.full_name:
            return
        self._update_in_progress(progress=data["progress"])

    @callback
    def _update_in_progress(self, progress: int | bool) -> None:
        """Update the download progress."""
        self._attr_in_progress = progress
        self.async_write_ha_state()
