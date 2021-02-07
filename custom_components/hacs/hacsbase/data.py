"""Data handler for HACS."""
import os

from queueman import QueueManager

from custom_components.hacs.const import INTEGRATION_VERSION
from custom_components.hacs.helpers.classes.manifest import HacsManifest
from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.helpers.functions.register_repository import (
    register_repository,
)
from custom_components.hacs.helpers.functions.store import (
    async_load_from_store,
    async_save_to_store,
    get_store_for_key,
)
from custom_components.hacs.share import get_hacs


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
        self.hacs.hass.bus.fire("hacs/config", {})

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
        if data:
            if repository.data.installed and (
                repository.data.installed_commit or repository.data.installed_version
            ):
                await async_save_to_store(
                    self.hacs.hass,
                    f"hacs/{repository.data.id}.hacs",
                    repository.data.to_json(),
                )
            self.content[str(repository.data.id)] = data

    async def restore(self):
        """Restore saved data."""
        hacs = await async_load_from_store(self.hacs.hass, "hacs")
        repositories = await async_load_from_store(self.hacs.hass, "repositories")
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
            stores = {}
            for entry in repositories or []:
                stores[entry] = get_store_for_key(self.hacs.hass, f"hacs/{entry}.hacs")

            stores_exist = {}

            def _populate_stores():
                for entry in repositories or []:
                    stores_exist[entry] = os.path.exists(stores[entry].path)

            await self.hacs.hass.async_add_executor_job(_populate_stores)

            # Repositories
            for entry in repositories or []:
                self.queue.add(
                    self.async_restore_repository(
                        entry, repositories[entry], stores[entry], stores_exist[entry]
                    )
                )

            await self.queue.execute()

            self.logger.info("Restore done")
        except (Exception, BaseException) as exception:  # pylint: disable=broad-except
            self.logger.critical(f"[{exception}] Restore Failed!")
            return False
        return True

    async def async_restore_repository(
        self, entry, repository_data, store, store_exists
    ):
        if not self.hacs.is_known(entry):
            await register_repository(
                repository_data["full_name"], repository_data["category"], False
            )
        repository = [
            x
            for x in self.hacs.repositories
            if str(x.data.id) == str(entry)
            or x.data.full_name == repository_data["full_name"]
        ]
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

        restored = store_exists and await store.async_load() or {}

        if restored:
            repository.data.update_data(restored)
            if not repository.data.installed:
                repository.logger.debug(
                    "Should be installed but is not... Fixing that!"
                )
                repository.data.installed = True
