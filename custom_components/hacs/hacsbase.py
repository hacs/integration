"""Blueprint for HacsBase."""
# pylint: disable=too-few-public-methods
import logging
import uuid

_LOGGER = logging.getLogger('custom_components.hacs.hacs')


class HacsBase:
    """The base class of HACS, nested thoughout the project."""
    data = {}
    hass = None
    config_dir = None
    github = None
    custom_repositories = {"integration": [], "plugin": []}
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
        from custom_components.hacs.handler.storage import write_to_data_store

        _LOGGER.debug(f"({repo}) - Trying to register")

        if element_type == "integration":
            repository = HacsRepositoryIntegration(repo)

        elif element_type == "plugin":
            repository = HacsRepositoryPlugin(repo)

        else:
            return False


        setup_result = None
        try:
            setup_result = await repository.setup_repository()
        except HacsBaseException as exception:
            _LOGGER.debug(exception)
            return setup_result

        if setup_result:
            if repository.custom:
                if repo.repository_name not in self.data["custom"][element_type]:
                    self.data["custom"][element_type].append(repo.repository_name)
            await write_to_data_store(self.config_dir, self.data)
            return True
        else:
            if repo not in self.blacklist:
                self.blacklist.append(repo)
            _LOGGER.debug(f"({repo}) - Could not register")
            return False
