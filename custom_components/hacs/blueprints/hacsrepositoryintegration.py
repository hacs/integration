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
        self._repository_name = repository_name
        self._repository_type = "integration"
        self._manifest_content = None

    @property
    def manifest_content(self):
        """
        Repository manifest content.

        Retruns a dict with the manifest content.
        """
        return "" if self._description is None else self._description


    async def setup_repository(self) -> None:
        """Run initialation to setup a repository."""
        self.validate_repository_name()

