"""Blueprint for HacsBase."""
# pylint: disable=too-few-public-methods
import logging
import uuid
from custom_components.hacs.aiogithub import AIOGitHubBaseException

_LOGGER = logging.getLogger('custom_components.hacs.hacs')


class HacsBase:
    """The base class of HACS, nested thoughout the project."""
    import custom_components.hacs.const as const

    migration = None
    storage = None
    data = {}
    hass = None
    config_dir = None
    aiogithub = None
    blacklist = []
    repositories = {}
    task_running = False

    url_path = {}
    for endpoint in ["api", "error", "overview", "static", "store", "settings", "repository"]:
        url_path[endpoint] = "/community_{}-{}".format(str(uuid.uuid4()), str(uuid.uuid4()))

    async def startup_tasks(self):
        """Run startup_tasks."""
        self.task_running = True

        _LOGGER.debug("Runing startup tasks.")

        custom_log_level = {"custom_components.hacs": "debug"}
        await self.hass.services.async_call("logger", "set_level", custom_log_level)

        #await self.setup_recuring_tasks()  # TODO: Check this...

        _LOGGER.info("Trying to load existing data.")

        await self.storage.get()

        if not self.repositories:
            _LOGGER.info("Expected data did not exist running initial setup, this will take some time.")
            self.repositories = {}
            self.data["hacs"] = {
                "local": self.const.VERSION,
                "remote": None,
                "schema": self.const.STORAGE_VERSION}
            await self.update_repositories()

        else:
            _LOGGER.warning("Migration logic goes here")

        # Make sure we have the correct version
        self.data["hacs"]["local"] = self.const.VERSION

        #await self.check_for_hacs_update()

        # Update installed element data on startup
        for element in self.repositories:
            element_object = self.repositories[element]
            if element_object.installed:
                await element_object.update()

        self.task_running = False

    async def register_new_repository(self, element_type, repo, repositoryobject=None):
        """Register a new repository."""
        from custom_components.hacs.exceptions import HacsBaseException, HacsRequirement
        from custom_components.hacs.blueprints import HacsRepositoryIntegration, HacsRepositoryPlugin

        _LOGGER.debug("(%s) - Trying to register", repo)

        if element_type == "integration":
            repository = HacsRepositoryIntegration(repo, repositoryobject)
            await repository.set_repository()

        elif element_type == "plugin":
            repository = HacsRepositoryPlugin(repo, repositoryobject)
            await repository.set_repository()

        else:
            return False

        setup_result = True
        self.task_running = True
        try:
            await repository.setup_repository()
        #except AIOGitHubBaseException as exception:
        #    _LOGGER.debug(exception)
        except HacsRequirement as exception:
            _LOGGER.debug(exception)
            setup_result = False
        except HacsBaseException as exception:
            _LOGGER.debug(exception)
            setup_result = False

        if setup_result:
            self.repositories[repository.repository_id] = repository
            await self.storage.set()

        else:
            if repo not in self.blacklist:
                self.blacklist.append(repo)
            _LOGGER.debug("(%s) - Could not register.", repo)
        return repository, setup_result

    async def update_repositories(self, notarealargument=None):
        """Run update on registerd repositories, and register new."""

        # Running update on registerd repositories
        if self.repositories:
            for repository in self.repositories:
                try:
                    repository = self.repositories[repository]
                    _LOGGER.info("Running update for %s", repository.repository_name)
                    await repository.update()
                except AIOGitHubBaseException as exception:
                    _LOGGER.warning(exception)

        # Register new repositories
        integrations, plugins = await self.get_repositories()

        repository_types = {"integration": integrations, "plugin": plugins}

        for repository_type in repository_types:
            for repository in repository_types[repository_type]:
                if repository.archived:
                    continue
                elif repository.full_name in self.blacklist:
                    continue
                else:
                    try:
                        await self.register_new_repository(repository_type, repository.full_name, repository)
                    except AIOGitHubBaseException as exception:
                        _LOGGER.warning(exception)

    async def get_repositories(self):
        """Get defined repositories."""
        repositories = {}

        # Get org repositories
        repositories["integration"] = await self.aiogithub.get_org_repos("custom-components")
        repositories["plugin"] = await self.aiogithub.get_org_repos("custom-cards")

        # Additional repositories (Not implemented)
        for repository_type in self.const.DEFAULT_REPOSITORIES:
            for repository in self.const.DEFAULT_REPOSITORIES[repository_type]:
                result = await self.aiogithub.get_repo(repository)
                repositories[repository_type].append(result)

        return repositories["integration"], repositories["plugin"]
