"""Data handler for HACS."""
import os
import json
from homeassistant.const import __version__ as HAVERSION
from integrationhelper import Logger
from . import Hacs
from .const import STORAGE_VERSION
from ..repositories.repositoryinformationview import RepositoryInformationView
from ..repositories.hacsrepositoryappdaemon import HacsRepositoryAppDaemon
from ..repositories.hacsrepositoryintegration import HacsRepositoryIntegration
from ..repositories.hacsrepositorybaseplugin import HacsRepositoryPlugin
from ..repositories.hacsrepositorypythonscript import HacsRepositoryPythonScripts
from ..repositories.hacsrepositorytheme import HacsRepositoryThemes

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
        if self.common.status.background_task:
            return

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
                "last_release_tag": repository.releases.last_release,
                "name": repository.information.name,
                "new": repository.status.new,
                "selected_tag": repository.status.selected_tag,
                "show_beta": repository.status.show_beta,
                "topics": repository.information.topics,
                "version_installed": repository.versions.installed,
            }
        save(path, content)

    def restore(self):
        """Restore saved data."""
        # Hacs
        content = self.read("hacs")
        if content is not None:
            content = content["data"]
            self.configuration.frontend_mode = content["view"]

        # Installed
        content = self.read("installed")
        if content is not None:
            content = content["data"]
            self.common.installed = content["data"]

        # Repositories
        content = self.read("repositories")
        if content is not None:
            content = content["data"]
            for repo in content:
                repo = content["repo"]
                self.logger.error(repo)


def save(path, content):
    """Save file."""
    content = {"data": content, "schema": STORAGE_VERSION}
    with open(path, "w", encoding="utf-8", errors="ignore") as storefile:
        json.dump(content, storefile, indent=4)


class OldHacsData:
    def restore_values(self):
        """Restore stored values."""

        path = STORES["hacs"]
        if os.path.exists(path):
            hacs = self.read("hacs")
            if hacs:
                self.frontend_mode = hacs.get("hacs", {}).get("view", "Grid")
                self.schema = hacs.get("hacs", {}).get("schema")
                self.endpoints = hacs.get("hacs", {}).get("endpoints", {})
                repositories = {}
                for repository in hacs.get("repositories", {}):
                    repo_id = repository
                    repository = hacs["repositories"][repo_id]

                    self.logger.info(repository["repository_name"], "restore")

                    if repository["repository_type"] == "appdaemon":
                        repositories[repo_id] = HacsRepositoryAppDaemon(
                            repository["repository_name"]
                        )

                    elif repository["repository_type"] == "integration":
                        repositories[repo_id] = HacsRepositoryIntegration(
                            repository["repository_name"]
                        )

                    elif repository["repository_type"] == "plugin":
                        repositories[repo_id] = HacsRepositoryPlugin(
                            repository["repository_name"]
                        )

                    elif repository["repository_type"] == "python_script":
                        repositories[repo_id] = HacsRepositoryPythonScripts(
                            repository["repository_name"]
                        )

                    elif repository["repository_type"] == "theme":
                        repositories[repo_id] = HacsRepositoryThemes(
                            repository["repository_name"]
                        )

                    else:
                        continue

                    repositories[repo_id].description = repository.get(
                        "description", ""
                    )
                    repositories[repo_id].installed = repository["installed"]
                    repositories[repo_id].last_commit = repository.get(
                        "last_commit", ""
                    )
                    repositories[repo_id].name = repository["name"]
                    repositories[repo_id].new = repository.get("new", True)
                    repositories[repo_id].repository_id = repo_id
                    repositories[repo_id].topics = repository.get("topics", [])
                    repositories[repo_id].track = repository.get("track", True)
                    repositories[repo_id].show_beta = repository.get("show_beta", False)
                    repositories[repo_id].version_installed = repository.get(
                        "version_installed"
                    )
                    repositories[repo_id].last_release_tag = repository.get(
                        "last_release_tag"
                    )
                    repositories[repo_id].installed_commit = repository.get(
                        "installed_commit"
                    )
                    repositories[repo_id].selected_tag = repository.get("selected_tag")
                    if repo_id == "172733314":
                        repositories[repo_id].version_installed = "x.x.x"
                    self.frontend.append(
                        RepositoryInformationView(repositories[repo_id])
                    )

                self.repositories = repositories
