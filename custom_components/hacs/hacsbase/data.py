"""Data handler for HACS."""
import os
import json
from integrationhelper import Logger
from . import Hacs
from .const import STORAGE_VERSION
from ..const import VERSION


STORES = {
    "hacs": "hacs.hacs",
    "installed": "hacs.installed",
    "repositories": "hacs.repositories",
}


class HacsData(Hacs):
    """HacsData class."""

    def __init__(self):
        """Initialize."""
        self.logger = Logger("hacs.data")

    def read(self, store):
        """Return data from a store."""
        path = f"{self.system.config_path}/.storage/{STORES[store]}"
        content = None
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as storefile:
                content = storefile.read()
                content = json.loads(content)
        return content

    def write(self):
        """Write content to the store files."""
        if self.system.status.background_task:
            return

        self.logger.debug("Saving data")

        # Hacs
        path = f"{self.system.config_path}/.storage/{STORES['hacs']}"
        content = {"view": self.configuration.frontend_mode}
        save(path, content)

        # Installed
        path = f"{self.system.config_path}/.storage/{STORES['installed']}"
        content = self.common.installed
        save(path, content)

        # Repositories
        path = f"{self.system.config_path}/.storage/{STORES['repositories']}"
        content = {}
        for repository in self.repositories:
            content[repository.information.uid] = {
                "authors": repository.information.authors,
                "category": repository.information.category,
                "description": repository.information.description,
                "full_name": repository.information.full_name,
                "hide": repository.status.hide,
                "installed_commit": repository.versions.installed_commit,
                "installed": repository.status.installed,
                "last_commit": repository.versions.available_commit,
                "last_release_tag": repository.versions.available,
                "name": repository.information.name,
                "new": repository.status.new,
                "selected_tag": repository.status.selected_tag,
                "pending_upgrade": repository.status.pending.upgrade,
                "show_beta": repository.status.show_beta,
                "version_installed": repository.versions.installed,
            }
        save(path, content)

    async def restore(self):
        """Restore saved data."""
        try:
            self.logger.info("Restore started")

            # Hacs
            content = self.read("hacs")
            content = content["data"]
            self.configuration.frontend_mode = content["view"]

            # Installed
            content = self.read("installed")
            content = content["data"]
            self.common.installed = content

            # Repositories
            content = self.read("repositories")
            content = content["data"]
            for entry in content:
                repo = content[entry]
                if repo["full_name"] != "custom-components/hacs":
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

                if repo.get("show_beta") is not None:
                    repository.status.show_beta = repo["show_beta"]

                if repo.get("pending_upgrade") is not None:
                    repository.status.pending.upgrade = repo["pending_upgrade"]

                if repo.get("last_commit") is not None:
                    repository.versions.available_commit = repo["last_commit"]

                if repo["full_name"] == "custom-components/hacs":
                    repository.versions.installed = VERSION
                    repository.status.new = False
                else:
                    repository.information.uid = entry

                    if repo.get("last_release_tag") is not None:
                        repository.releases.last_release = repo["last_release_tag"]
                        repository.versions.available = repo["last_release_tag"]

                    if repo.get("new") is not None:
                        repository.status.new = repo["new"]

                    if repo.get("version_installed") is not None:
                        repository.versions.installed = repo["version_installed"]

                    if repo.get("installed_commit") is not None:
                        repository.versions.installed_commit = repo["installed_commit"]

            self.logger.info("Restore done")
        except Exception as exception:
            self.logger.critical(f"[{exception}] Restore Failed!")
            return False
        return True


def save(path, content):
    """Save file."""
    content = {"data": content, "schema": STORAGE_VERSION}
    with open(path, "w", encoding="utf-8", errors="ignore") as storefile:
        json.dump(content, storefile, indent=4)
