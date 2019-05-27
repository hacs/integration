"""Blueprint for HacsBase."""
# pylint: disable=too-few-public-methods
import logging
import uuid
import json
import aiofiles

_LOGGER = logging.getLogger('custom_components.hacs.hacs')


class HacsBase:
    """The base class of HACS, nested thoughout the project."""
    import custom_components.hacs.const as const
    data = {}
    hass = None
    config_dir = None
    github = None
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


    async def register_new_repository(self, element_type, repo):
        """Register a new repository."""
        from custom_components.hacs.exceptions import HacsBaseException
        from custom_components.hacs.blueprints import HacsRepositoryIntegration, HacsRepositoryPlugin

        _LOGGER.debug(f"({repo}) - Trying to register")

        if element_type == "integration":
            repository = HacsRepositoryIntegration(repo)

        elif element_type == "plugin":
            repository = HacsRepositoryPlugin(repo)

        else:
            return False


        setup_result = None
        self.task_running = True
        try:
            setup_result = await repository.setup_repository()
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

        # Skip attributes that can't be stored, or we want to clear on restart.
        skip_attributes = [
            "content_objects",
            "last_release_object",
            "pending_restart",
            "repository",
            "track",
            "reasons",
        ]

        for repository in self.repositories:
            repositorydata = {}
            repository = self.repositories[repository]
            attributes = vars(repository)
            for key in attributes:
                if key not in skip_attributes:
                    repositorydata[key] = attributes[key]

            data["repositories"][attributes["repository_id"]] = repositorydata

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

                # Set repository attributes from stored values
                for attribute in repositorydata:
                    repository.__setattr__(attribute, repositorydata[attribute])

                # Restore complete
                self.repositories[repository.repository_id] = repository

        except Exception as exception:
            msg = "Could not load data from {} - {}".format(datastore, exception)
            _LOGGER.error(msg)
