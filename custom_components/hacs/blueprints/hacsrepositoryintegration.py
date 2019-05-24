"""Blueprint for HacsRepositoryIntegration."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except
from asyncio import sleep
import logging

from custom_components.hacs.blueprints import HacsRepositoryBase

_LOGGER = logging.getLogger(__name__)

class HacsRepositoryIntegration(HacsRepositoryBase):
    """
    Set up a HacsRepositoryIntegration object.

    repository_name(str): The full name of a repository
    (example: awesome-dev/awesome-repo)
    """

    def __init__(self, repository_name: str):
        """Initialize a HacsRepositoryIntegration object."""

        super().__init__()
        self.repository_name = repository_name
        self.repository_type = "integration"
        self.manifest_content = None

    async def setup_repository(self):
        """
        Run initialation to setup a repository.

        Return True if everything is validated and ok.
        """
        try:
            # Validate the repository name
            self.validate_repository_name()
            await sleep(0.2)

            # Set the Gihub repository object
            self.set_repository()
            await sleep(0.2)

        except self.HacsRepositoryInfo as exception:
            _LOGGER.error(f"Could not validate/setup repository info - {exception}")
            return False

        except Exception as exception:
            raise self.HacsNotSoBasicException(
                f"An unexpected error occured while trying to setup repository - {exception}")

        # If we get there all is good.
        return True
