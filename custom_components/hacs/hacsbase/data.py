"""Data handler for HACS."""
import os
import asyncio

from queueman import QueueManager

from custom_components.hacs.const import INTEGRATION_VERSION
from custom_components.hacs.helpers.classes.manifest import HacsManifest
from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.helpers.functions.register_repository import (
    register_repository,
)
from custom_components.hacs.helpers.functions.store import (
    async_load_from_store,
    async_save_to_store_default_encoder,
    async_save_to_store,
    get_store_for_key,
)
from custom_components.hacs.share import get_hacs

from homeassistant.core import callback


@callback
def async_update_repository_from_storage(repository, storage_data):
    """Merge in data from storage into the repo data."""
    repository.data.memorize_storage(storage_data)
    repository.data.update_data(storage_data)
    if repository.data.installed:
        return

    repository.logger.debug("Should be installed but is not... Fixing that!")
    repository.data.installed = True


class HacsData:
    """HacsData class."""

    def __init__(self):
        """Initialize."""
        self.logger = getLogger()
        self.hacs = get_hacs()
        self.queue = QueueManager()
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
            },
        )

        # Repositories
        self.content = {}
        for repository in self.hacs.repositories or []:
            self.queue.add(self.async_store_repository_data(repository))

        if not self.queue.has_pending_tasks:
            self.logger.debug("Nothing in the queue")
        elif self.queue.running:
            self.logger.debug("Queue is already running")
        else:
            await self.queue.execute()
        await async_save_to_store(self.hacs.hass, "repositories", self.content)
        self.hacs.hass.bus.async_fire("hacs/repository", {})
        self.hacs.hass.bus.async_fire("hacs/config", {})

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
        repositories = await async_load_from_store(self.hacs.hass, "repositories") or []
        try:
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

            # Repositories
            hacs_repos_by_id = {
                str(repo.data.id): repo for repo in self.hacs.repositories
            }

            tasks = []
            for entry, repo_data in repositories.items():
                full_name = repo_data["full_name"]
                if not (repo := hacs_repos_by_id.get(entry)):
                    self.logger.error(f"Did not find {full_name} ({entry})")
                    continue
                tasks.append(self.async_restore_repository(entry, repo_data, repo))

            # Repositories
            await asyncio.gather(*tasks)

            entries_from_storage = {}

            def _load_from_storage():
                for entry in repositories:
                    store = get_store_for_key(self.hacs.hass, f"hacs/{entry}.hacs")
                    if not os.path.exists(store.path):
                        continue
                    data = store.load()
                    if data:
                        entries_from_storage[entry] = data

            await self.hacs.hass.async_add_executor_job(_load_from_storage)

            for entry in entries_from_storage:
                async_update_repository_from_storage(
                    hacs_repos_by_id[entry], entries_from_storage[entry]
                )

            self.logger.info("Restore done")
        except (Exception, BaseException) as exception:  # pylint: disable=broad-except
            self.logger.critical(f"[{exception}] Restore Failed!", exc_info=exception)
            return False
        return True

    async def async_restore_repository(self, entry, repository_data, repository):
        if not self.hacs.is_known(entry):
            await register_repository(
                repository_data["full_name"], repository_data["category"], False
            )

        if not repository:
            self.logger.error(f"Did not find {repository_data['full_name']} ({entry})")
            return

        repository = repository[0]

        # Restore repository attributes
        repository.data.id = entry
        repository.data.authors = repository_data.get("authors", [])
        repository.data.description = repository_data.get("description")
        repository.releases.last_release_object_downloads = repository_data.get(
            "downloads"
        )
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
            repository.data.installed_version = INTEGRATION_VERSION
            repository.data.installed = True
