"""Blueprint for HacsRepositoryIntegration."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except
from asyncio import sleep
import logging

from homeassistant.helpers.event import async_call_later
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
            # Check the blacklist
            if self.repository_name in self.blacklist:
                raise self.HacsBlacklistException

            # If a previous attempt failed we need to reset the track flag
            self.track = True

            # Validate the repository name
            self.validate_repository_name()
            await sleep(0.2)

            # Set the Gihub repository object
            self.set_repository()
            await sleep(0.2)

            # Set repository ID
            self.set_repository_id()
            await sleep(0.2)

            # Set repository releases
            self.set_repository_releases()
            await sleep(0.2)

            # Set the repository ref
            self.set_ref()
            await sleep(0.2)

            # Set additional info
            self.set_additional_info()
            await sleep(0.2)


        except self.HacsRepositoryInfo as exception:
            _LOGGER.error(f"Could not validate/setup repository info - {exception}")
            return False

        except self.HacsUserScrewupException as exception:
            _LOGGER.error(exception)
            return False

        except Exception as exception:
            raise self.HacsNotSoBasicException(
                f"An unexpected error occured while trying to setup repository - {exception}")

        # If we get there all is good.
        return True

    async def install(self):
        """Run install tasks."""
        try:
            # Run common checks
            await self.common_check()
            await sleep(0.2)


        except self.HacsRepositoryInfo as exception:
            _LOGGER.error(f"Could not validate/setup repository info - {exception}")
            return False

        except self.HacsUserScrewupException as exception:
            _LOGGER.error(exception)
            return False

        except Exception as exception:
            raise self.HacsNotSoBasicException(
                f"An unexpected error occured while trying to setup repository - {exception}")

    async def remove(self):
        """Run remove tasks."""

    async def uninstall(self):
        """Run uninstall tasks."""

    async def update(self):
        """Run update tasks."""
        try:
            # Update description.
            self.set_description()
            await sleep(0.2)

            # Run common checks
            await self.common_check()
            await sleep(0.2)


        except self.HacsRepositoryInfo as exception:
            _LOGGER.error(f"Could not validate/setup repository info - {exception}")
            return False

        except self.HacsUserScrewupException as exception:
            _LOGGER.error(exception)
            return False

        except Exception as exception:
            raise self.HacsNotSoBasicException(
                f"An unexpected error occured while trying to setup repository - {exception}")

    def start_task_scheduler(self):
        """Start task scheduler."""
        if not self.installed:
            return

        # Update installed elements every 30min
        async_call_later(self.hass, 60*30, self.update)

    async def common_check(self):
        """Common checks for most operations."""
        try:
            # Check if last updated string changed.
            current = self.last_updated
            new = self.return_last_update()
            if current == new:
                return

            # Validate content.
            await self.setup_repository()
            await sleep(0.2)

            # Print log
            self.log_repository_info()


        except self.HacsRepositoryInfo as exception:
            _LOGGER.error(f"Could not validate/setup repository info - {exception}")
            return False

        except self.HacsUserScrewupException as exception:
            _LOGGER.error(exception)
            return False

        except Exception as exception:
            raise self.HacsNotSoBasicException(
                f"An unexpected error occured while trying to setup repository - {exception}")
