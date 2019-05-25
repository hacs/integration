"""Blueprint for HacsBase."""
# pylint: disable=too-few-public-methods
import logging
import uuid

_LOGGER = logging.getLogger(__name__)


class HacsBase:
    """The base class of HACS, nested thoughout the project."""
    data = {}
    hass = None
    config_dir = None
    github = None
    custom_repositories = {"integration": [], "plugin": []}
    blacklist = []
    elements = {}
    task_running = False
    url_path = {
        "overview": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
        "store": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
        "settings": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
        "repo": f"/community_{str(uuid.uuid4())}-{str(uuid.uuid4())}",
    }


    async def register_new_repository(self, element_type, repo):
        """Register a new repository."""
        from custom_components.hacs.exceptions import HacsBaseException
        from custom_components.hacs.blueprints import HacsRepositoryIntegration
        from custom_components.hacs.handler.storage import write_to_data_store

        if element_type != "integration":
            return
        repository = HacsRepositoryIntegration(repo)

        setup_result = None
        try:
            setup_result = await repository.setup_repository()
        except HacsBaseException as exception:
            _LOGGER.debug(exception)
            return setup_result

        if setup_result:
            self.data["elements"][repository.repository_id] = repository
            if repository.custom:
                self.data["repos"][element_type].append(repo)
            write_to_data_store(self.config_dir, self.data)
        else:
            _LOGGER.debug(f"Could not register {repo}")
