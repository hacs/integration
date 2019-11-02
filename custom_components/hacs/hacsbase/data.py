"""Data handler for HACS."""
import os
import json
from integrationhelper import Logger
from . import Hacs
from .const import STORAGE_VERSION
from ..const import VERSION
from ..repositories.manifest import HacsManifest
from ..store import async_save_to_store, async_load_from_store


STORES = {
    "old": "hacs",
    "hacs": "hacs.hacs",
    "installed": "hacs.installed",
    "repositories": "hacs.repositories",
}


class HacsData(Hacs):
    """HacsData class."""

    def __init__(self):
        """Initialize."""
        self.logger = Logger("hacs.data")

    def check_corrupted_files(self):
        """Return True if one (or more) of the files are corrupted."""
        for store in STORES:
            path = f"{self.system.config_path}/.storage/{STORES[store]}"
            if os.path.exists(path):
                if os.stat(path).st_size == 0:
                    # File is empty (corrupted)
                    return True
        return False

    def read(self, store):
        """Return data from a store."""
        path = f"{self.system.config_path}/.storage/{STORES[store]}"
        content = None
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as storefile:
                content = storefile.read()
                content = json.loads(content)
        return content

    async def async_write(self):
        """Write content to the store files."""
        if self.system.status.background_task:
            return

        self.logger.debug("Saving data")

        # Hacs
        await async_save_to_store(
            self.hass, "hacs", {"view": self.configuration.frontend_mode}
        )

        # Repositories
        content = {}
        for repository in self.repositories:
            if repository.repository_manifest is not None:
                repository_manifest = repository.repository_manifest.manifest
            else:
                repository_manifest = None
            content[repository.information.uid] = {
                "authors": repository.information.authors,
                "topics": repository.information.topics,
                "category": repository.information.category,
                "description": repository.information.description,
                "full_name": repository.information.full_name,
                "hide": repository.status.hide,
                "installed_commit": repository.versions.installed_commit,
                "installed": repository.status.installed,
                "last_commit": repository.versions.available_commit,
                "last_release_tag": repository.versions.available,
                "repository_manifest": repository_manifest,
                "name": repository.information.name,
                "new": repository.status.new,
                "selected_tag": repository.status.selected_tag,
                "show_beta": repository.status.show_beta,
                "version_installed": repository.versions.installed,
            }

        await async_save_to_store(self.hass, "repositories", content)
        self.hass.bus.async_fire("hacs/repository", {})
        self.hass.bus.fire("hacs/config", {})

    async def restore(self):
        """Restore saved data."""
        hacs = {}
        repositories = {}

        try:
            hacs = await async_load_from_store(self.hass, "hacs")
        except KeyError:
            await async_save_to_store(self.hass, "hacs", self.data.read("hacs")["data"])
            hacs = await async_load_from_store(self.hass, "hacs")

        try:
            repositories = await async_load_from_store(self.hass, "repositories")
        except KeyError:
            await async_save_to_store(
                self.hass, "repositories", self.data.read("repositories")["data"]
            )
            repositories = await async_load_from_store(self.hass, "repositories")

        try:
            if self.check_corrupted_files():
                # Coruptted installation
                self.logger.critical("Restore failed one or more files are corrupted!")
                return False
            if hacs is None and repositories is None:
                # Assume new install
                return True

            self.logger.info("Restore started")

            # Hacs
            self.configuration.frontend_mode = hacs.get("view", "Grid")

            # Repositories
            repositories = repositories
            for entry in repositories:
                repo = repositories[entry]
                if repo["full_name"] == "custom-components/hacs":
                    # Skip the old repo location
                    continue
                if not self.is_known(repo["full_name"]):
                    await self.register_repository(
                        repo["full_name"], repo["category"], False
                    )
                repository = self.get_by_name(repo["full_name"])
                if repository is None:
                    self.logger.error(f"Did not find {repo['full_name']}")
                    continue

                # Restore repository attributes
                if repo.get("authors") is not None:
                    repository.information.authors = repo["authors"]

                if repo.get("topics", []):
                    repository.information.topics = repo["topics"]

                if repo.get("description") is not None:
                    repository.information.description = repo["description"]

                if repo.get("name") is not None:
                    repository.information.name = repo["name"]

                if repo.get("hide") is not None:
                    repository.status.hide = repo["hide"]

                if repo.get("installed") is not None:
                    repository.status.installed = repo["installed"]
                    if repository.status.installed:
                        repository.status.first_install = False

                if repo.get("selected_tag") is not None:
                    repository.status.selected_tag = repo["selected_tag"]

                if repo.get("repository_manifest") is not None:
                    repository.repository_manifest = HacsManifest.from_dict(
                        repo["repository_manifest"]
                    )

                if repo.get("show_beta") is not None:
                    repository.status.show_beta = repo["show_beta"]

                if repo.get("last_commit") is not None:
                    repository.versions.available_commit = repo["last_commit"]

                repository.information.uid = entry

                if repo.get("last_release_tag") is not None:
                    repository.releases.last_release = repo["last_release_tag"]
                    repository.versions.available = repo["last_release_tag"]

                if repo.get("new") is not None:
                    repository.status.new = repo["new"]

                if repo["full_name"] == "hacs/integration":
                    repository.versions.installed = VERSION
                    repository.status.installed = True
                    if "b" in VERSION:
                        repository.status.show_beta = True
                elif repo.get("version_installed") is not None:
                    repository.versions.installed = repo["version_installed"]

                if repo.get("installed_commit") is not None:
                    repository.versions.installed_commit = repo["installed_commit"]

            self.logger.info("Restore done")
        except Exception as exception:
            self.logger.critical(
                f"[{exception}] Restore Failed! see https://github.com/hacs/integration/issues/639 for more details."
            )
            return False
        return True


def save(logger, path, content):
    """Save file."""
    from .backup import Backup

    backup = Backup(path)
    backup.create()
    try:
        content = {"data": content, "schema": STORAGE_VERSION}
        with open(path, "w", encoding="utf-8") as storefile:
            json.dump(content, storefile, indent=4)
    except Exception as exception:  # pylint: disable=broad-except
        logger.warning(f"Saving {path} failed - {exception}")
        backup.restore()
    backup.cleanup()
