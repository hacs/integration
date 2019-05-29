"""Blueprint for HacsBase."""
# pylint: disable=too-few-public-methods
import logging
import uuid
import json
import aiofiles
import asyncio
from custom_components.hacs.aiogithub import AIOGitHubBaseException

_LOGGER = logging.getLogger('custom_components.hacs.hacs')


class HacsBase:
    """The base class of HACS, nested thoughout the project."""
    import custom_components.hacs.const as const
    data = {}
    hass = None
    config_dir = None
    github = None
    aiogithub = None
    blacklist = []
    repositories = {}
    task_running = False
    url_path = {
        "api": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
        "error": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
        "overview": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
        "static": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
        "store": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
        "settings": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
        "repository": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
    }


    async def register_new_repository(self, element_type, repo, repositoryobject=None):
        """Register a new repository."""
        from custom_components.hacs.exceptions import HacsBaseException
        from custom_components.hacs.blueprints import HacsRepositoryIntegration, HacsRepositoryPlugin

        _LOGGER.debug(f"({repo}) - Trying to register")

        if element_type == "integration":
            repository = HacsRepositoryIntegration(repo, repositoryobject)
            await repository.set_arepository()

        elif element_type == "plugin":
            repository = HacsRepositoryPlugin(repo, repositoryobject)
            await repository.set_arepository()

        else:
            return False


        setup_result = None
        self.task_running = True
        try:
            setup_result = await repository.setup_repository()
        except AIOGitHubBaseException as exception:
            _LOGGER.debug(exception)
        except HacsBaseException as exception:
            _LOGGER.debug(exception)
            return setup_result

        if setup_result:
            self.repositories[repository.repository_id] = repository
            await self.write_to_data_store()

        else:
            if repo not in self.blacklist:
                self.blacklist.append(repo)
            _LOGGER.debug(f"({repo}) - Could not register")
        return repository, setup_result


    async def write_to_data_store(self):
        """
        Write data to datastore.
        """
        datastore = "{}/.storage/{}".format(self.config_dir, self.const.STORENAME)

        data = {}
        data["hacs"] = self.data["hacs"]

        data["repositories"] = {}

        for repository in self.repositories:
            repositorydata = {}
            repository = self.repositories[repository]

            repositorydata["hide"] = repository.hide
            repositorydata["installed"] = repository.installed
            repositorydata["name"] = repository.name
            repositorydata["repository_name"] = repository.repository_name
            repositorydata["repository_type"] = repository.repository_type
            repositorydata["show_beta"] = repository.show_beta
            repositorydata["version_installed"] = repository.version_installed

            data["repositories"][repository.repository_id] = repositorydata

        try:
            async with aiofiles.open(
                datastore, mode='w', encoding="utf-8", errors="ignore") as outfile:
                await outfile.write(json.dumps(data, indent=4))
                outfile.close()

        except Exception as error:
            msg = "Could not write data to {} - {}".format(datastore, error)
            _LOGGER.error(msg)


    async def get_data_from_store(self):
        """
        Get data from datastore.
        Returns a dict with information from the storage.
        example output: {"repositories": {}, "hacs": {}}
        """
        from custom_components.hacs.blueprints import (
            HacsRepositoryIntegration,
            HacsRepositoryPlugin,)
        datastore = "{}/.storage/{}".format(self.config_dir, self.const.STORENAME)
        _LOGGER.debug("Reading from datastore %s.", datastore)

        try:
            async with aiofiles.open(
                datastore, mode='r', encoding="utf-8", errors="ignore") as datafile:
                store_data = await datafile.read()
                store_data = json.loads(store_data)
                datafile.close()

            # Restore data about HACS
            self.data["hacs"] = store_data["hacs"]

            # Restore repository data
            for repository in store_data["repositories"]:
                # Set var
                repositorydata = store_data["repositories"][repository]

                _LOGGER.info("Loading %s from storrage.", repositorydata["repository_name"])

                # Restore integration
                if repositorydata["repository_type"] == "integration":
                    repository = HacsRepositoryIntegration(repositorydata["repository_name"])

                # Restore plugin
                elif repositorydata["repository_type"] == "plugin":
                    repository = HacsRepositoryPlugin(repositorydata["repository_name"])

                # Not supported
                else:
                    continue

                # Attach AIOGitHub object
                await repository.set_arepository()

                # Set repository attributes from stored values
                for attribute in repositorydata:
                    repository.__setattr__(attribute, repositorydata[attribute])

                # Restore complete
                self.repositories[repository.repository_id] = repository

        except Exception as exception:
            msg = "Could not load data from {} - {}".format(datastore, exception)
            _LOGGER.error(msg)


    async def full_repository_scan(self, notarealargument=None):
        """Full repository scan."""
        integration_repos, plugin_repos = await self.get_repositories()

        repos = {"integration": integration_repos, "plugin": plugin_repos}

        _LOGGER.debug(f"Blacklist {self.blacklist}")

        for element_type in repos:
            for repository in repos[element_type]:
                _LOGGER.debug(f"Checking {repository.full_name}")
                if repository.full_name in self.blacklist:
                    _LOGGER.debug(f"Skipping {repository.full_name}")
                    continue

                if str(repository.id) not in self.repositories:
                    self.hass.async_create_task(self.register_new_repository(element_type, repository.full_name, repository))

                else:
                    repository = self.repositories[str(repository.id)]
                    self.hass.async_create_task(repository.update())

                await asyncio.sleep(5)

    def get_repos(self):
        """Get org and custom repos."""

        integration_repos = self.get_repos_integration()
        plugin_repos = self.get_repos_plugin()

        return integration_repos, plugin_repos

    def get_repos_integration(self):
        """Get org and custom integration repos."""
        repositories = []

        # Org repos
        for repository in list(self.github.get_organization("custom-components").get_repos()):
            if repository.archived:
                continue
            if repository.full_name in self.blacklist:
                continue
            repositories.append(repository)

        return repositories

    def get_repos_plugin(self):
        """Get org and custom plugin repos."""
        repositories = []
        ## Org repos
        for repository in list(self.github.get_organization("custom-cards").get_repos()):
            if repository.archived:
                continue
            if repository.full_name in self.blacklist:
                continue
            repositories.append(repository)

        return repositories

    async def update_repositories(self):
        """Run update on registerd repositories, and register new."""

        # Running update on registerd repositories
        for repository in self.repositories:
            await self.repositories[repository].update()

        # Register new repositories
        integrations, plugins = await self.get_repositories()

        ## Integrations
        for repository in integrations:
            if repository.archived:
                continue
            elif repository.full_name in self.blacklist:
                continue
            else:
                await self.register_new_repository("integration", repository.full_name, repository)

        # Plugins
        for repository in plugins:
            if repository.archived:
                continue
            elif repository.full_name in self.blacklist:
                continue
            else:
                await self.register_new_repository("integration", repository.full_name, repository)

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
