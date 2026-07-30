"""Class for wake word models in HACS."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.exceptions import HomeAssistantError

from ..enums import HacsCategory, HacsDispatchEvent
from ..exceptions import HacsException
from ..utils.decorator import concurrent
from .base import HacsRepository

if TYPE_CHECKING:
    from ..base import HacsBase


class HacsWakeWordRepository(HacsRepository):
    """Wake word models in HACS."""

    def __init__(self, hacs: HacsBase, full_name: str):
        """Initialize."""
        super().__init__(hacs=hacs)
        self.data.full_name = full_name
        self.data.full_name_lower = full_name.lower()
        self.data.category = HacsCategory.WAKE_WORD
        self.content.path.remote = "custom_wake_words"
        self.content.path.local = self.localpath
        self.content.single = False

    @property
    def localpath(self):
        """Return localpath.

        The full name (owner/repo) is used, rather than just the repo name, so
        that two repositories with the same repo name but different owners do not
        collide on disk. Home Assistant derives the wake word id from the path
        relative to custom_wake_words/, so this also keeps those ids unique.
        """
        return f"{self.hacs.core.config_path}/custom_wake_words/{self.data.full_name}"

    async def validate_repository(self):
        """Validate."""
        # Run common validation steps.
        await self.common_validate()

        # Custom step 1: Validate content.
        if self.repository_manifest.content_in_root:
            self.content.path.remote = ""

        compliant = False
        for treefile in self.treefiles:
            if treefile.startswith(self.content.path.remote) and treefile.endswith(".tflite"):
                compliant = True
                break
        if not compliant:
            raise HacsException(
                f"{self.string} Repository structure for {self.ref.replace('tags/', '')} "
                "is not compliant"
            )

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.hacs.status.startup:
                    self.logger.error("%s %s", self.string, error)
        return self.validate.success

    async def async_post_installation(self):
        """Run post installation steps."""
        await self._reload_custom_wake_words()

    async def async_post_uninstall(self):
        """Run post uninstall steps."""
        await self._reload_custom_wake_words()

    async def _reload_custom_wake_words(self) -> None:
        """Ask esphome to rescan the custom wake word directory.

        The wake word inventory is cached for the lifetime of the Home Assistant
        process, so installing, updating or removing a model has no effect until
        the cache is invalidated. The esphome integration exposes a service that
        does this and refreshes the satellites.
        """
        if not self.hacs.hass.services.has_service("esphome", "reload_custom_wake_words"):
            return
        self.logger.debug("%s Reloading custom wake words", self.string)
        try:
            await self.hacs.hass.services.async_call("esphome", "reload_custom_wake_words", {})
        except HomeAssistantError as exception:
            self.logger.exception("%s %s", self.string, exception)

    @concurrent(concurrenttasks=10, backoff_time=5)
    async def update_repository(self, ignore_issues=False, force=False):
        """Update."""
        if not await self.common_update(ignore_issues, force) and not force:
            return

        # Get wake word model objects.
        if self.repository_manifest.content_in_root:
            self.content.path.remote = ""

        # Set local path
        self.content.path.local = self.localpath

        # Signal frontend to refresh
        if self.data.installed:
            self.hacs.async_dispatch(
                HacsDispatchEvent.REPOSITORY,
                {
                    "id": 1337,
                    "action": "update",
                    "repository": self.data.full_name,
                    "repository_id": self.data.id,
                },
            )
