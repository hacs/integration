"""Data handler for HACS."""
import os
import json
from homeassistant.const import __version__ as HAVERSION
from .const import STORENAME, VERSION
from ..handler.logger import HacsLogger
from ..repositories.repositoryinformationview import RepositoryInformationView
from ..repositories.hacsrepositoryappdaemon import HacsRepositoryAppDaemon
from ..repositories.hacsrepositoryintegration import HacsRepositoryIntegration
from ..repositories.hacsrepositorybaseplugin import HacsRepositoryPlugin
from ..repositories.hacsrepositorypythonscript import HacsRepositoryPythonScripts
from ..repositories.hacsrepositorytheme import HacsRepositoryThemes
from ..repositories.repositoryinformationview import RepositoryInformationView

class HacsData:
    """HacsData class."""

    def __init__(self, config_dir):
        """Initialize."""
        self.frontend_mode = "Grid"
        self.repositories = {}
        self.logger = HacsLogger()
        self.config_dir = config_dir
        self.ha_version = HAVERSION
        self.schema = None
        self.endpoints = {}
        self.frontend = []
        self.task_running = False

    @property
    def store_path(self):
        """Return the path to the store file."""
        return "{}/.storage/{}".format(self.config_dir, STORENAME)

    def read(self):
        """Read from store."""
        content = None
        try:
            with open(self.store_path, "r", encoding="utf-8", errors="ignore") as storefile:
                content = storefile.read()
                content = json.loads(content)
        except FileNotFoundError:
            pass
        return content

    def write(self):
        """Write to store."""
        if self.task_running:
            return

        self.logger.debug("Saving data", "store")

        data = {
            "hacs": {
                "view": self.frontend_mode,
                "schema": self.schema,
                "endpoints": self.endpoints
            },
            "repositories": {}
        }

        for repository in self.repositories:
            repository = self.repositories[repository]
            repositorydata = {
                "custom": repository.custom,
                "description": repository.description,
                "hide": repository.hide,
                "installed_commit": repository.installed_commit,
                "installed": repository.installed,
                "last_commit": repository.last_commit,
                "name": repository.name,
                "new": repository.new,
                "repository_name": repository.repository_name,
                "repository_type": repository.repository_type,
                "show_beta": repository.show_beta,
                "topics": repository.topics,
                "track": repository.track,
                "last_release_tag": repository.last_release_tag,
                "version_installed": repository.version_installed,
                "selected_tag": repository.selected_tag,
            }


            data["repositories"][repository.repository_id] = repositorydata

        try:
            with open(self.store_path, "w", encoding="utf-8", errors="ignore") as storefile:
                json.dump(data, storefile, indent=4)
        except FileNotFoundError:
            pass

    def repository(self, repository_id):
        """Retrurn the stored repository object, or None."""
        repository_object = None
        if repository_id in self.repositories:
            repository_object = self.repositories[repository_object]
        return repository_object

    def restore_values(self):
        """Restore stored values."""
        if os.path.exists(self.store_path):
            store = self.read()
            if store:
                self.frontend_mode = store.get("hacs", {}).get("view", "Grid")
                self.schema = store.get("hacs", {}).get("schema")
                self.endpoints = store.get("hacs", {}).get("endpoints", {})
                repositories = {}
                for repository in store.get("repositories", {}):
                    repo_id = repository
                    repository = store["repositories"][repo_id]

                    self.logger.info(repository["repository_name"], "restore")

                    if repository["repository_type"] == "appdaemon":
                        repositories[repo_id] = HacsRepositoryAppDaemon(repository["repository_name"])

                    elif repository["repository_type"] == "integration":
                        repositories[repo_id] = HacsRepositoryIntegration(repository["repository_name"])

                    elif repository["repository_type"] == "plugin":
                        repositories[repo_id] = HacsRepositoryPlugin(repository["repository_name"])

                    elif repository["repository_type"] == "python_script":
                        repositories[repo_id] = HacsRepositoryPythonScripts(repository["repository_name"])

                    elif repository["repository_type"] == "theme":
                        repositories[repo_id] = HacsRepositoryThemes(repository["repository_name"])

                    else:
                        continue

                    repositories[repo_id].description = repository.get("description", "")
                    repositories[repo_id].installed = repository["installed"]
                    repositories[repo_id].last_commit = repository.get("last_commit", "")
                    repositories[repo_id].name = repository["name"]
                    repositories[repo_id].new = repository.get("new", True)
                    repositories[repo_id].repository_id = repo_id
                    repositories[repo_id].topics = repository.get("topics", [])
                    repositories[repo_id].track = repository.get("track", True)
                    repositories[repo_id].show_beta = repository.get("show_beta", False)
                    repositories[repo_id].version_installed = repository.get("version_installed")
                    repositories[repo_id].last_release_tag = repository.get("last_release_tag")
                    repositories[repo_id].installed_commit = repository.get("installed_commit")
                    repositories[repo_id].selected_tag = repository.get("selected_tag")
                    if repo_id == "172733314":
                        repositories[repo_id].version_installed = VERSION
                    self.frontend.append(RepositoryInformationView(repositories[repo_id]))

                self.repositories = repositories
