"""Data handler for HACS."""
import asyncio
from datetime import datetime
import os

from homeassistant.core import callback
from homeassistant.util import json as json_util

from ..base import HacsBase
from ..enums import HacsGitHubRepo
from ..repositories.base import HacsManifest, HacsRepository
from .logger import get_hacs_logger
from .path import is_safe
from .store import (
    async_load_from_store,
    async_save_to_store,
    async_save_to_store_default_encoder,
    get_store_for_key,
)


def update_repository_from_storage(repository, storage_data):
    """Merge in data from storage into the repo data."""
    repository.data.memorize_storage(storage_data)
    repository.data.update_data(storage_data)
    if repository.data.installed:
        return

    repository.logger.debug("%s Should be installed but is not... Fixing that!", repository)
    repository.data.installed = True


class HacsData:
    """HacsData class."""

    def __init__(self, hacs: HacsBase):
        """Initialize."""
        self.logger = get_hacs_logger()
        self.hacs = hacs
        self.content = {}

    async def async_write(self, force: bool = False) -> None:
        """Write content to the store files."""
        if not force and self.hacs.system.disabled:
            return

        self.logger.debug("Saving data")

        # Hacs
        await async_save_to_store(
            self.hacs.hass,
            "hacs",
            {
                "view": self.hacs.configuration.frontend_mode,
                "compact": self.hacs.configuration.frontend_compact,
                "onboarding_done": self.hacs.configuration.onboarding_done,
                "archived_repositories": self.hacs.common.archived_repositories,
                "renamed_repositories": self.hacs.common.renamed_repositories,
                "ignored_repositories": self.hacs.common.ignored_repositories,
            },
        )
        await self._async_store_content_and_repos()
        for event in ("hacs/repository", "hacs/config"):
            self.hacs.hass.bus.async_fire(event, {})

    async def _async_store_content_and_repos(self):  # bb: ignore
        """Store the main repos file and each repo that is out of date."""
        # Repositories
        self.content = {}
        # Not run concurrently since this is bound by disk I/O
        for repository in self.hacs.repositories.list_all:
            await self.async_store_repository_data(repository)

        await async_save_to_store(self.hacs.hass, "repositories", self.content)

    async def async_store_repository_data(self, repository: HacsRepository):
        repository_manifest = repository.repository_manifest.manifest
        data = {
            "authors": repository.data.authors,
            "category": repository.data.category,
            "description": repository.data.description,
            "domain": repository.data.domain,
            "downloads": repository.data.downloads,
            "etag_repository": repository.data.etag_repository,
            "full_name": repository.data.full_name,
            "first_install": repository.status.first_install,
            "installed_commit": repository.data.installed_commit,
            "installed": repository.data.installed,
            "last_commit": repository.data.last_commit,
            "last_release_tag": repository.data.last_version,
            "last_updated": repository.data.last_updated,
            "name": repository.data.name,
            "new": repository.data.new,
            "repository_manifest": repository_manifest,
            "releases": repository.data.releases,
            "selected_tag": repository.data.selected_tag,
            "show_beta": repository.data.show_beta,
            "stars": repository.data.stargazers_count,
            "topics": repository.data.topics,
            "version_installed": repository.data.installed_version,
        }
        if repository.data.last_fetched:
            data["last_fetched"] = repository.data.last_fetched.timestamp()

        self.content[str(repository.data.id)] = data

        if (
            repository.data.installed
            and (repository.data.installed_commit or repository.data.installed_version)
            and (export := repository.data.export_data())
        ):
            # export_data will return `None` if the memorized
            # data is already up to date which allows us to avoid
            # writing data that is already up to date or generating
            # executor jobs to check the data on disk to see
            # if a write is needed.
            await async_save_to_store_default_encoder(
                self.hacs.hass,
                f"hacs/{repository.data.id}.hacs",
                export,
            )
            repository.data.memorize_storage(export)

    async def restore(self):
        """Restore saved data."""
        self.hacs.status.new = False
        hacs = await async_load_from_store(self.hacs.hass, "hacs") or {}
        repositories = await async_load_from_store(self.hacs.hass, "repositories") or {}

        if not hacs and not repositories:
            # Assume new install
            self.hacs.status.new = True
            self.logger.info("Loading base repository information")
            repositories = await self.hacs.hass.async_add_executor_job(
                json_util.load_json,
                f"{self.hacs.core.config_path}/custom_components/hacs/utils/default.repositories",
            )

        self.logger.info("Restore started")

        # Hacs
        self.hacs.configuration.frontend_mode = hacs.get("view", "Grid")
        self.hacs.configuration.frontend_compact = hacs.get("compact", False)
        self.hacs.configuration.onboarding_done = hacs.get("onboarding_done", False)
        self.hacs.common.archived_repositories = []
        self.hacs.common.ignored_repositories = []
        self.hacs.common.renamed_repositories = {}

        # Clear out doubble renamed values
        renamed = hacs.get("renamed_repositories", {})
        for entry in renamed:
            value = renamed.get(entry)
            if value not in renamed:
                self.hacs.common.renamed_repositories[entry] = value

        # Clear out doubble archived values
        for entry in hacs.get("archived_repositories", []):
            if entry not in self.hacs.common.archived_repositories:
                self.hacs.common.archived_repositories.append(entry)

        # Clear out doubble ignored values
        for entry in hacs.get("ignored_repositories", []):
            if entry not in self.hacs.common.ignored_repositories:
                self.hacs.common.ignored_repositories.append(entry)

        hass = self.hacs.hass
        stores = {}

        try:
            await self.register_unknown_repositories(repositories)

            for entry, repo_data in repositories.items():
                if entry == "0":
                    # Ignore repositories with ID 0
                    self.logger.debug("Found repository with ID %s - %s", entry, repo_data)
                    continue
                if self.async_restore_repository(entry, repo_data):
                    stores[entry] = get_store_for_key(hass, f"hacs/{entry}.hacs")

            def _load_from_storage():
                for entry, store in stores.items():
                    if os.path.exists(store.path) and (data := store.load()):
                        if (full_name := data.get("full_name")) and (
                            renamed := self.hacs.common.renamed_repositories.get(full_name)
                        ) is not None:
                            data["full_name"] = renamed
                        update_repository_from_storage(
                            self.hacs.repositories.get_by_id(entry), data
                        )

            await hass.async_add_executor_job(_load_from_storage)
            self.logger.info("Restore done")
        except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            self.logger.critical(f"[{exception}] Restore Failed!", exc_info=exception)
            return False
        return True

    async def register_unknown_repositories(self, repositories):
        """Registry any unknown repositories."""
        register_tasks = [
            self.hacs.async_register_repository(
                repository_full_name=repo_data["full_name"],
                category=repo_data["category"],
                check=False,
                repository_id=entry,
            )
            for entry, repo_data in repositories.items()
            if entry != "0" and not self.hacs.repositories.is_registered(repository_id=entry)
        ]
        if register_tasks:
            await asyncio.gather(*register_tasks)

    @callback
    def async_restore_repository(self, entry, repository_data):
        full_name = repository_data["full_name"]
        if not (repository := self.hacs.repositories.get_by_full_name(full_name)):
            self.logger.error(f"Did not find {full_name} ({entry})")
            return False
        # Restore repository attributes
        self.hacs.repositories.set_repository_id(repository, entry)
        repository.data.authors = repository_data.get("authors", [])
        repository.data.description = repository_data.get("description")
        repository.releases.last_release_object_downloads = repository_data.get("downloads")
        repository.data.last_updated = repository_data.get("last_updated")
        repository.data.etag_repository = repository_data.get("etag_repository")
        repository.data.topics = repository_data.get("topics", [])
        repository.data.domain = repository_data.get("domain", None)
        repository.data.stargazers_count = repository_data.get("stars", 0)
        repository.releases.last_release = repository_data.get("last_release_tag")
        repository.data.releases = repository_data.get("releases")
        repository.data.hide = repository_data.get("hide", False)
        repository.data.installed = repository_data.get("installed", False)
        repository.data.new = repository_data.get("new", True)
        repository.data.selected_tag = repository_data.get("selected_tag")
        repository.data.show_beta = repository_data.get("show_beta", False)
        repository.data.last_version = repository_data.get("last_release_tag")
        repository.data.last_commit = repository_data.get("last_commit")
        repository.data.installed_version = repository_data.get("version_installed")
        repository.data.installed_commit = repository_data.get("installed_commit")

        if last_fetched := repository_data.get("last_fetched"):
            repository.data.last_fetched = datetime.fromtimestamp(last_fetched)

        repository.repository_manifest = HacsManifest.from_dict(
            repository_data.get("repository_manifest", {})
        )

        if repository.localpath is not None and is_safe(self.hacs, repository.localpath):
            # Set local path
            repository.content.path.local = repository.localpath

        if repository.data.installed:
            repository.status.first_install = False

        if full_name == HacsGitHubRepo.INTEGRATION:
            repository.data.installed_version = self.hacs.version
            repository.data.installed = True

        return True
