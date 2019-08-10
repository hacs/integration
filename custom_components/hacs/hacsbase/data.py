"""Data handler for HACS."""
import os
import json
from integrationhelper import Logger
from . import Hacs
from .const import STORAGE_VERSION
from ..const import VERSION


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

    def write(self):
        """Write content to the store files."""
        if self.system.status.background_task:
            return

        self.logger.debug("Saving data")

        # Hacs
        path = f"{self.system.config_path}/.storage/{STORES['hacs']}"
        hacs = {"view": self.configuration.frontend_mode}
        save(path, hacs)

        # Installed
        path = f"{self.system.config_path}/.storage/{STORES['installed']}"
        installed = {}
        for repository in self.common.installed:
            repository = self.get_by_name(repository)
            installed[repository.information.full_name] = {
                "version_type": repository.display_version_or_commit,
                "version_installed": repository.display_installed_version,
                "version_available": repository.display_available_version,
            }
        save(path, installed)

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
                "show_beta": repository.status.show_beta,
                "version_installed": repository.versions.installed,
            }

        # Validate installed repositories
        count_installed = len(installed) + 1  # For HACS it self
        count_installed_restore = 0
        for repository in self.repositories:
            if repository.status.installed:
                count_installed_restore += 1

        if count_installed < count_installed_restore:
            self.logger.debug("Save failed!")
            self.logger.debug(
                f"Number of installed repositories does not match the number of stored repositories [{count_installed} vs {count_installed_restore}]"
            )
            return
        save(path, content)

    async def restore(self):
        """Restore saved data."""
        try:
            hacs = self.read("hacs")
            installed = self.read("installed")
            repositrories = self.read("repositories")
            if self.check_corrupted_files():
                # Coruptted installation
                self.logger.critical("Restore failed one or more files are corrupted!")
                return False
            if hacs is None and installed is None and repositrories is None:
                # Assume new install
                return True

            self.logger.info("Restore started")

            # Hacs
            hacs = hacs["data"]
            self.configuration.frontend_mode = hacs["view"]

            # Installed
            installed = installed["data"]
            for repository in installed:
                self.common.installed.append(repository)

            # Repositories
            repositrories = repositrories["data"]
            for entry in repositrories:
                repo = repositrories[entry]
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

                if repo.get("last_commit") is not None:
                    repository.versions.available_commit = repo["last_commit"]

                repository.information.uid = entry

                if repo.get("last_release_tag") is not None:
                    repository.releases.last_release = repo["last_release_tag"]
                    repository.versions.available = repo["last_release_tag"]

                if repo.get("new") is not None:
                    repository.status.new = repo["new"]

                if repo["full_name"] == "custom-components/hacs":
                    repository.versions.installed = VERSION
                    if "b" in VERSION:
                        repository.status.show_beta = True
                elif repo.get("version_installed") is not None:
                    repository.versions.installed = repo["version_installed"]

                if repo.get("installed_commit") is not None:
                    repository.versions.installed_commit = repo["installed_commit"]

                if repo["full_name"] in self.common.installed:
                    repository.status.installed = True
                    repository.status.new = False
                    frominstalled = installed[repo["full_name"]]
                    if frominstalled["version_type"] == "commit":
                        repository.versions.installed_commit = frominstalled[
                            "version_installed"
                        ]
                        repository.versions.available_commit = frominstalled[
                            "version_available"
                        ]
                    else:
                        repository.versions.installed = frominstalled[
                            "version_installed"
                        ]
                        repository.versions.available = frominstalled[
                            "version_available"
                        ]

            # Check the restore.
            count_installed = len(installed) + 1  # For HACS it self
            count_installed_restore = 0
            installed_restore = []
            for repository in self.repositories:
                if repository.status.installed:
                    installed_restore.append(repository.information.full_name)
                    if (
                        repository.information.full_name not in self.common.installed
                        and repository.information.full_name != "custom-components/hacs"
                    ):
                        self.logger.warning(
                            f"{repository.information.full_name} is not in common.installed"
                        )
                    count_installed_restore += 1

            if count_installed < count_installed_restore:
                for repo in installed:
                    installed_restore.remove(repo)
                self.logger.warning(f"Check {repo}")

                self.logger.critical("Restore failed!")
                self.logger.critical(
                    f"Number of installed repositories does not match the number of restored repositories [{count_installed} vs {count_installed_restore}]"
                )
                return False

            self.logger.info("Restore done")
        except Exception as exception:
            self.logger.critical(f"[{exception}] Restore Failed!")
            return False
        return True


def save(path, content):
    """Save file."""
    from .backup import Backup

    backup = Backup(path)
    backup.create()
    try:
        content = {"data": content, "schema": STORAGE_VERSION}
        with open(path, "w", encoding="utf-8") as storefile:
            json.dump(content, storefile, indent=4)
    except Exception:  # pylint: disable=broad-except
        backup.restore()
    backup.cleanup()
