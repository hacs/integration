"""Initialize the HACS base."""
# pylint: disable=unused-argument, bad-continuation
import json
import uuid
from datetime import timedelta

from homeassistant.helpers.event import async_call_later, async_track_time_interval

from integrationhelper import Logger

from ..aiogithub.exceptions import AIOGitHubException, AIOGitHubRatelimit
from ..handler.logger import HacsLogger
from .const import ELEMENT_TYPES


class HacsStatus:
    """HacsStatus."""

    startup = True
    background_task = True


class HacsCommon:
    """Common for HACS."""

    status = HacsStatus()
    categories = None
    blacklist = []
    default = []


class System:
    """System info."""

    config_path = None
    ha_version = None
    status = HacsStatus()


class Developer:
    """Developer settings/tools."""

    template_id = "Repository ID"
    template_content = ""
    template_raw = ""

    @property
    def devcontainer(self):
        """Is it a devcontainer?"""
        import os

        if "DEVCONTAINER" in os.environ:
            return True
        return False


class Hacs:
    """The base class of HACS, nested thoughout the project."""

    token = f"{str(uuid.uuid4())}-{str(uuid.uuid4())}"
    hacsweb = f"/hacsweb/{token}"
    hacsapi = f"/hacsapi/{token}"
    repositories = []
    developer = Developer()
    data = None
    configuration = None
    logger = Logger("hacs")
    github = None
    hass = None
    version = None
    system = System()
    common = HacsCommon()

    async def register_repository(self, full_name, category):
        """Register a repository."""
        from ..repositories.repository import RERPOSITORY_CLASSES

        if category not in RERPOSITORY_CLASSES:
            self.logger.error(f"{category} is not a valid repository category.")
            return False

        repository = RERPOSITORY_CLASSES[category](full_name)
        await repository.registration()
        if repository.validate.errors:
            self.logger.error(f"Validation for {full_name} failed.")
            return repository.validate.errors

        self.repositories.append(repository)
        repository.logger.info("Registration complete")

    async def startup_tasks(self):
        """Tasks tha are started after startup."""

    def get_by_id(self, repository_id):
        """Get repository by ID."""
        try:
            for repository in self.repositories:
                if repository.repository_id == repository_id:
                    return repository
        except Exception:  # pylint: disable=broad-except
            pass
        return None

    def get_by_name(self, repository_full_name):
        """Get repository by full_name."""
        try:
            for repository in self.repositories:
                if repository.information.full_name == repository_full_name:
                    return repository
        except Exception:  # pylint: disable=broad-except
            pass
        return None

    def is_known(self, repository_full_name):
        """Return a bool if the repository is known."""
        for repository in self.repositories:
            if repository.information.full_name == repository_full_name:
                return True
        return False

    @property
    def sorted_by_name(self):
        """Return a sorted(by name) list of repository objects."""
        return sorted(self.repositories, key=lambda x: x.information.name.lower())

    @property
    def sorted_by_repository_name(self):
        """Return a sorted(by repository_name) list of repository objects."""
        return sorted(self.repositories, key=lambda x: x.information.full_name)


class HacsBase:
    """The base class of HACS, nested thoughout the project."""

    const = None
    hacsconst = None
    migration = None
    storage = None
    hacs = None
    dev_template = ""
    dev_template_id = "Repository ID"
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
        from .startup import HacsStartup

        await HacsStartup().run_startup()
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
        from ..repositories.hacsrepositorypythonscript import (
            HacsRepositoryPythonScripts,
        )
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
                self.logger.error(
                    "{} - {}".format(repository.repository_name, exception)
                )
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

        self.logger.debug(
            "Skipping repositories in blacklist {}".format(str(self.blacklist))
        )

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
                        self.logger.info("Running update", repository.repository_name)
                        await repository.update()
                except AIOGitHubException as exception:
                    self.logger.error(
                        "{} - {}".format(repository.repository_name, exception)
                    )

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
                        self.logger.error(
                            "{} - {}".format(repository.repository_name, exception)
                        )
        self.store.task_running = False
        self.store.write()

    async def get_repositories(self):
        """Get defined repositories."""
        if Hacs.configuration.dev:
            if Hacs.developer.devcontainer:
                return (
                    [await self.aiogithub.get_repo("ludeeus/ad-hacs")],
                    [
                        await self.aiogithub.get_repo("custom-components/hacs"),
                        await self.aiogithub.get_repo("ludeeus/integration-hacs"),
                    ],
                    [await self.aiogithub.get_repo("maykar/compact-custom-header")],
                    [await self.aiogithub.get_repo("ludeeus/ps-hacs")],
                    [await self.aiogithub.get_repo("ludeeus/theme-hacs")],
                )

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
                self.logger.error(
                    "{} - {}".format(repository.repository_name, exception)
                )
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
