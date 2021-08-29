"""Data handler for HACS."""
import asyncio
import os

from homeassistant.core import callback

from custom_components.hacs.helpers.classes.manifest import HacsManifest
from custom_components.hacs.helpers.functions.register_repository import (
    register_repository,
)
from custom_components.hacs.helpers.functions.store import (
    async_load_from_store,
    async_save_to_store,
    async_save_to_store_default_encoder,
    get_store_for_key,
)
from custom_components.hacs.share import get_hacs
from custom_components.hacs.utils.logger import getLogger


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

    def __init__(self):
        """Initialize."""
        self.logger = getLogger()
        self.hacs = get_hacs()
        self.content = {}

    async def async_write(self):
        """Write content to the store files."""
        if self.hacs.status.background_task or self.hacs.system.disabled:
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
                "etag_hacs_default": self.hacs._etag_hacs_default,  # pylint: disable=protected-access
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
        for repository in self.hacs.repositories:
            await self.async_store_repository_data(repository)

        await async_save_to_store(self.hacs.hass, "repositories", self.content)

    async def async_store_repository_data(self, repository):
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
            "selected_tag": repository.data.selected_tag,
            "show_beta": repository.data.show_beta,
            "stars": repository.data.stargazers_count,
            "topics": repository.data.topics,
            "version_installed": repository.data.installed_version,
        }
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
        hacs = await async_load_from_store(self.hacs.hass, "hacs")
        repositories = await async_load_from_store(self.hacs.hass, "repositories") or {}

        if not hacs and not repositories:
            # Assume new install
            self.hacs.status.new = True
            return True
        self.logger.info("Restore started")
        self.hacs.status.new = False

        # Hacs
        self.hacs.configuration.frontend_mode = hacs.get("view", "Grid")
        self.hacs.configuration.frontend_compact = hacs.get("compact", False)
        self.hacs.configuration.onboarding_done = hacs.get("onboarding_done", False)
        self.hacs.common.archived_repositories = hacs.get("archived_repositories", [])
        self.hacs.common.renamed_repositories = hacs.get("renamed_repositories", {})
        self.hacs._etag_hacs_default = hacs.get(  # pylint: disable=protected-access
            "etag_hacs_default", {}
        )

        # Repositories
        hass = self.hacs.hass
        stores = {}

        try:
            await self.register_unknown_repositories(repositories)

            for entry, repo_data in repositories.items():
                if self.async_restore_repository(entry, repo_data):
                    stores[entry] = get_store_for_key(hass, f"hacs/{entry}.hacs")

            def _load_from_storage():
                for entry, store in stores.items():
                    if os.path.exists(store.path) and (data := store.load()):
                        update_repository_from_storage(self.hacs.get_by_id(entry), data)

            await hass.async_add_executor_job(_load_from_storage)
            self.logger.info("Restore done")
        except (Exception, BaseException) as exception:  # pylint: disable=broad-except
            self.logger.critical(f"[{exception}] Restore Failed!", exc_info=exception)
            return False
        return True

    async def register_unknown_repositories(self, repositories):
        """Registry any unknown repositories."""
        register_tasks = [
            register_repository(repo_data["full_name"], repo_data["category"], False)
            for entry, repo_data in repositories.items()
            if not self.hacs.is_known(entry)
        ]
        if register_tasks:
            await asyncio.gather(*register_tasks)

    @callback
    def async_restore_repository(self, entry, repository_data):
        full_name = repository_data["full_name"]
        if not (repository := self.hacs.get_by_name(full_name)):
            self.logger.error(f"Did not find {full_name} ({entry})")
            return False
        # Restore repository attributes
        self.hacs.async_set_repository_id(repository, entry)
        repository.data.authors = repository_data.get("authors", [])
        repository.data.description = repository_data.get("description")
        repository.releases.last_release_object_downloads = repository_data.get("downloads")
        repository.data.last_updated = repository_data.get("last_updated")
        repository.data.etag_repository = repository_data.get("etag_repository")
        repository.data.topics = repository_data.get("topics", [])
        repository.data.domain = repository_data.get("domain", None)
        repository.data.stargazers_count = repository_data.get("stars", 0)
        repository.releases.last_release = repository_data.get("last_release_tag")
        repository.data.hide = repository_data.get("hide", False)
        repository.data.installed = repository_data.get("installed", False)
        repository.data.new = repository_data.get("new", True)
        repository.data.selected_tag = repository_data.get("selected_tag")
        repository.data.show_beta = repository_data.get("show_beta", False)
        repository.data.last_version = repository_data.get("last_release_tag")
        repository.data.last_commit = repository_data.get("last_commit")
        repository.data.installed_version = repository_data.get("version_installed")
        repository.data.installed_commit = repository_data.get("installed_commit")

        repository.repository_manifest = HacsManifest.from_dict(
            repository_data.get("repository_manifest", {})
        )

        if repository.data.installed:
            repository.status.first_install = False

        if repository_data["full_name"] == "hacs/integration":
            repository.data.installed_version = self.hacs.version
            repository.data.installed = True

        return True
