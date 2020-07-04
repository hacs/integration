from custom_components.hacs.hacs import get_hacs
from custom_components.hacs.helpers.functions.register_repository import (
    register_repository,
)
from custom_components.hacs.helpers.functions.information import get_repository
from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.const import VERSION


async def async_load_hacs_repository():
    """Load HACS repositroy."""
    hacs = get_hacs()

    try:
        repository = hacs.get_by_name("hacs/integration")
        if repository is None:
            await register_repository("hacs/integration", "integration")
            repository = hacs.get_by_name("hacs/integration")
        if repository is None:
            raise HacsException("Unknown error")
        repository.data.installed = True
        repository.data.installed_version = VERSION
        repository.data.new = False
        hacs.repo = repository.repository_object
        hacs.data_repo = await get_repository(
            hacs.session, hacs.configuration.token, "hacs/default"
        )
    except HacsException as exception:
        if "403" in f"{exception}":
            hacs.logger.critical("GitHub API is ratelimited, or the token is wrong.")
        else:
            hacs.logger.critical(f"[{exception}] - Could not load HACS!")
        return False
    return True
