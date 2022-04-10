"""Class for integrations in HACS."""
from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from homeassistant.loader import async_get_custom_components

from ..enums import HacsCategory, HacsGitHubRepo, RepositoryFile
from ..exceptions import AddonRepositoryException, HacsException
from ..utils.decode import decode_content
from ..utils.decorator import concurrent
from ..utils.filters import get_first_directory_in_directory
from ..utils.version import version_to_download
from .base import HacsRepository

if TYPE_CHECKING:
    from ..base import HacsBase


class HacsIntegrationRepository(HacsRepository):
    """Integrations in HACS."""

    def __init__(self, hacs: HacsBase, full_name: str):
        """Initialize."""
        super().__init__(hacs=hacs)
        self.data.full_name = full_name
        self.data.full_name_lower = full_name.lower()
        self.data.category = HacsCategory.INTEGRATION
        self.content.path.remote = "custom_components"
        self.content.path.local = self.localpath

    @property
    def localpath(self):
        """Return localpath."""
        return f"{self.hacs.core.config_path}/custom_components/{self.data.domain}"

    async def async_post_installation(self):
        """Run post installation steps."""
        if self.data.config_flow:
            if self.data.full_name != HacsGitHubRepo.INTEGRATION:
                await self.reload_custom_components()
            if self.data.first_install:
                self.pending_restart = False
                return
        self.pending_restart = True

    async def validate_repository(self):
        """Validate."""
        await self.common_validate()

        # Custom step 1: Validate content.
        if self.data.content_in_root:
            self.content.path.remote = ""

        if self.content.path.remote == "custom_components":
            name = get_first_directory_in_directory(self.tree, "custom_components")
            if name is None:
                if (
                    "repository.json" in self.treefiles
                    or "repository.yaml" in self.treefiles
                    or "repository.yml" in self.treefiles
                ):
                    raise AddonRepositoryException()
                raise HacsException(
                    f"Repository structure for {self.ref.replace('tags/','')} is not compliant"
                )
            self.content.path.remote = f"custom_components/{name}"

        # Get the content of manifest.json
        if manifest := await self.async_get_integration_manifest():
            try:
                self.integration_manifest = manifest
                self.data.authors = manifest["codeowners"]
                self.data.domain = manifest["domain"]
                self.data.manifest_name = manifest["name"]
                self.data.config_flow = manifest.get("config_flow", False)

            except KeyError as exception:
                self.validate.errors.append(
                    f"Missing expected key '{exception}' in { RepositoryFile.MAINIFEST_JSON}"
                )
                self.hacs.log.error(
                    "Missing expected key '%s' in '%s'", exception, RepositoryFile.MAINIFEST_JSON
                )

        # Set local path
        self.content.path.local = self.localpath

        # Handle potential errors
        if self.validate.errors:
            for error in self.validate.errors:
                if not self.hacs.status.startup:
                    self.logger.error("%s %s", self.string, error)
        return self.validate.success

    @concurrent(concurrenttasks=10, backoff_time=5)
    async def update_repository(self, ignore_issues=False, force=False):
        """Update."""
        if not await self.common_update(ignore_issues, force) and not force:
            return

        if self.data.content_in_root:
            self.content.path.remote = ""

        if self.content.path.remote == "custom_components":
            name = get_first_directory_in_directory(self.tree, "custom_components")
            self.content.path.remote = f"custom_components/{name}"

        # Get the content of manifest.json
        if manifest := await self.async_get_integration_manifest():
            try:
                self.integration_manifest = manifest
                self.data.authors = manifest["codeowners"]
                self.data.domain = manifest["domain"]
                self.data.manifest_name = manifest["name"]
                self.data.config_flow = manifest.get("config_flow", False)

            except KeyError as exception:
                self.validate.errors.append(
                    f"Missing expected key '{exception}' in { RepositoryFile.MAINIFEST_JSON}"
                )
                self.hacs.log.error(
                    "Missing expected key '%s' in '%s'", exception, RepositoryFile.MAINIFEST_JSON
                )

        # Set local path
        self.content.path.local = self.localpath

        # Signal entities to refresh
        if self.data.installed:
            self.hacs.hass.bus.async_fire(
                "hacs/repository",
                {
                    "id": 1337,
                    "action": "update",
                    "repository": self.data.full_name,
                    "repository_id": self.data.id,
                },
            )

    async def reload_custom_components(self):
        """Reload custom_components (and config flows)in HA."""
        self.logger.info("Reloading custom_component cache")
        del self.hacs.hass.data["custom_components"]
        await async_get_custom_components(self.hacs.hass)
        self.logger.info("Custom_component cache reloaded")

    async def async_get_integration_manifest(self, ref: str = None) -> dict[str, Any] | None:
        """Get the content of the manifest.json file."""
        manifest_path = (
            "manifest.json"
            if self.data.content_in_root
            else f"{self.content.path.remote}/{RepositoryFile.MAINIFEST_JSON}"
        )

        if not manifest_path in (x.full_path for x in self.tree):
            raise HacsException(f"No {RepositoryFile.MAINIFEST_JSON} file found '{manifest_path}'")

        response = await self.hacs.async_github_api_method(
            method=self.hacs.githubapi.repos.contents.get,
            repository=self.data.full_name,
            path=manifest_path,
            **{"params": {"ref": ref or version_to_download(self)}},
        )
        if response:
            return json.loads(decode_content(response.data.content))
