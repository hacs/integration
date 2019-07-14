"""Initialize the HACS base."""
"""# pylint: disable=too-few-public-methods,unused-argument"""

import uuid
import json
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from ..aiogithub.exceptions import AIOGitHubException, AIOGitHubRatelimit
from .const import ELEMENT_TYPES
from ..handler.logger import HacsLogger

class HacsBase:
    """The base class of HACS, nested thoughout the project."""

    const = None
    hacsconst = None
    migration = None
    storage = None
    hacs = None
    ha_version = None
    config = None
    logger = HacsLogger()
    data = {"hacs": {}}
    data["task_running"] = True
    hass = None
    _default_repositories = []
    config_dir = None
    aiogithub = None
    blacklist = []
    store = None
    hacs_github = None
    repositories = {}

    url_path = {}
    for endpoint in [
            "api",
            "admin",
            "admin-api",
            "base",
            "error",
            "overview",
            "static",
            "store",
            "settings",
            "repository",
    ]:
        url_path[endpoint] = "/community_{}-{}".format(
            str(uuid.uuid4()), str(uuid.uuid4())
        )
    token = "{}-{}".format(str(uuid.uuid4()), str(uuid.uuid4()))
    hacsweb = "/hacsweb/{}".format(token)
    hacsapi = "/hacsapi/{}".format(token)

    async def startup_tasks(self, notarealargument=None):
        """Run startup_tasks."""
        self.store.task_running = True

        self.logger.info("Runing startup tasks.")

        self.logger.debug(self.token, "token")

        # Store enpoints
        self.data["hacs"]["endpoints"] = self.url_path

        try:
            self.logger.info("Trying to load existing data.")

            # Check if migration is needed, or load existing data.
            await self.migration.validate()

            await self.recuring_tasks_installed(True)

            # Update repository lists
            await self.get_repositories()

        except AIOGitHubRatelimit as exception:
            self.logger.critical(exception)
            self.logger.info("HACS will try to run setup again in 15 minuttes.")
            async_call_later(self.hass, 900, self.startup_tasks)
            return False

        # For installed repositories only.
        async_track_time_interval(
            self.hass, self.recuring_tasks_installed, timedelta(minutes=30)
        )

        # For the rest.
        async_track_time_interval(
            self.hass, self.update_repositories, timedelta(minutes=500)
        )

        self.store.task_running = False
        return True

    async def register_new_repository(self, element_type, repo, repositoryobject=None):
        """Register a new repository."""
        from .exceptions import HacsBaseException, HacsRequirement
        from ..repositories.repositoryinformationview import RepositoryInformationView
        from ..repositories.hacsrepositoryappdaemon import HacsRepositoryAppDaemon
        from ..repositories.hacsrepositoryintegration import HacsRepositoryIntegration
        from ..repositories.hacsrepositorybaseplugin import HacsRepositoryPlugin
        from ..repositories.hacsrepositorypythonscript import HacsRepositoryPythonScripts
        from ..repositories.hacsrepositorytheme import HacsRepositoryThemes

        if await self.is_known_repository(repo):
            return

        self.logger.info("Starting repository registration", repo)

        if element_type not in ELEMENT_TYPES:
            self.logger.info("is not enabled, skipping registration", element_type)
            return None, False

        if element_type == "appdaemon":
            repository = HacsRepositoryAppDaemon(repo, repositoryobject)

        elif element_type == "integration":
            repository = HacsRepositoryIntegration(repo, repositoryobject)

        elif element_type == "plugin":
            repository = HacsRepositoryPlugin(repo, repositoryobject)

        elif element_type == "python_script":
            repository = HacsRepositoryPythonScripts(repo, repositoryobject)

        elif element_type == "theme":
            repository = HacsRepositoryThemes(repo, repositoryobject)

        else:
            return None, False

        setup_result = True
        try:
            if not self.store.task_running:
                await repository.set_repository()
            await repository.setup_repository()
        except (HacsRequirement, HacsBaseException, AIOGitHubException) as exception:
            if not self.store.task_running:
                self.logger.error("{} - {}".format(repository.repository_name, exception))
            setup_result = False

        if setup_result:
            self.store.repositories[repository.repository_id] = repository
            self.store.frontend.append(RepositoryInformationView(repository))

        else:
            if repo not in self.blacklist:
                self.blacklist.append(repo)
            if not self.store.task_running:
                self.logger.error("Could not register.", repo)
        return repository, setup_result

    async def update_repositories(self, now=None):
        """Run update on registerd repositories, and register new."""
        self.store.task_running = True

        self.logger.debug("Skipping repositories in blacklist {}".format(str(self.blacklist)))

        # Running update on registerd repositories
        if self.store.repositories:
            for repository in self.store.repositories:
                try:
                    repository = self.store.repositories[repository]
                    if (
                        not repository.track
                        or repository.repository_name in self.blacklist
                    ):
                        continue
                    if repository.hide and repository.repository_id != "172733314":
                        continue
                    if now is not None:
                        self.logger.info(
                            "Running update", repository.repository_name
                        )
                        await repository.update()
                except AIOGitHubException as exception:
                    self.logger.error("{} - {}".format(repository.repository_name, exception))

        # Register new repositories
        appdaemon, integrations, plugins, python_scripts, themes = (
            await self.get_repositories()
        )

        repository_types = {
            "appdaemon": appdaemon,
            "integration": integrations,
            "plugin": plugins,
            "python_script": python_scripts,
            "theme": themes,
        }

        for repository_type in repository_types:
            for repository in repository_types[repository_type]:
                if repository.archived:
                    continue
                elif repository.full_name in self.blacklist:
                    continue
                elif str(repository.id) in self.store.repositories:
                    repository = self.store.repositories[str(repository.id)]
                    await repository.set_repository()
                else:
                    try:
                        await self.register_new_repository(
                            repository_type, repository.full_name, repository
                        )
                    except AIOGitHubException as exception:
                        self.logger.error("{} - {}".format(repository.repository_name, exception))
        self.store.task_running = False
        self.store.write()

    async def get_repositories(self):
        """Get defined repositories."""
        repositories = {
            "appdaemon": [],
            "integration": [],
            "plugin": [],
            "python_script": [],
            "theme": [],
        }

        self.logger.info("Fetching updated blacklist")
        blacklist = await self.hacs_github.get_contents(
            "repositories/blacklist", "data"
        )

        for item in json.loads(blacklist.content):
            if item not in self.blacklist:
                self.blacklist.append(item)

        # Remove blacklisted repositories
        for repository in self.blacklist:
            self.logger.debug(repository, "blacklist")
            if await self.is_known_repository(repository):
                repository = await self.get_repository_by_name(repository)
                await repository.remove()

        # Get org repositories
        repositories["integration"] = await self.aiogithub.get_org_repos(
            "custom-components"
        )
        repositories["plugin"] = await self.aiogithub.get_org_repos("custom-cards")

        # Additional default repositories
        for repository_type in ELEMENT_TYPES:
            self.logger.info("Fetching updated repository list", repository_type)
            default_repositories = await self.hacs_github.get_contents(
                "repositories/{}".format(repository_type), "data"
            )
            for repository in json.loads(default_repositories.content):
                if repository not in self._default_repositories:
                    self._default_repositories.append(repository)

                if not await self.is_known_repository(repository):
                    result = await self.aiogithub.get_repo(repository)
                    repositories[repository_type].append(result)

        return (
            repositories["appdaemon"],
            repositories["integration"],
            repositories["plugin"],
            repositories["python_script"],
            repositories["theme"],
        )

    async def recuring_tasks_installed(
        self, notarealarg
    ):  # pylint: disable=unused-argument
        """Recuring tasks for installed repositories."""
        self.store.task_running = True
        self.logger.info("Running scheduled update of installed repositories")
        for repository in self.store.repositories:
            try:
                repository = self.store.repositories[repository]
                if not repository.track or repository.repository_name in self.blacklist:
                    continue
                if not repository.installed:
                    continue
                self.logger.info("Running update", repository.repository_name)
                await repository.update()
            except AIOGitHubException as exception:
                self.logger.error("{} - {}".format(repository.repository_name, exception))
        self.store.task_running = False

    @property
    def repositories_list_name(self):
        """Return a sorted(by name) list of repository objects."""
        repositories = []
        for repository in self.store.repositories:
            repositories.append(self.store.repositories[repository])
        return sorted(repositories, key=lambda x: x.name.lower())

    @property
    def repositories_list_repo(self):
        """Return a sorted(by repository_name) list of repository objects."""
        repositories = []
        for repository in self.store.repositories:
            repositories.append(self.store.repositories[repository])
        return sorted(repositories, key=lambda x: x.repository_name)

    async def is_known_repository(self, repository_full_name):
        """Return a bool if the repository is known."""
        for repository in self.store.repositories:
            repository = self.store.repositories[repository]
            if repository.repository_name == repository_full_name:
                return True
        return False

    async def get_repository_by_name(self, repository_name):
        """Return a repository by it's name."""
        for repository in self.store.repositories:
            repository = self.store.repositories[repository]
            if repository.repository_name == repository_name:
                return repository
