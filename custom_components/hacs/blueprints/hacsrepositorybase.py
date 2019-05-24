"""Blueprint for HacsRepositoryBase."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except,wildcard-import
from asyncio import sleep
import logging

from custom_components.hacs.blueprints import HacsBase

_LOGGER = logging.getLogger(__name__)

class HacsRepositoryBase(HacsBase):
    """HacsRepoBase Class"""
    from custom_components.hacs.exceptions import HacsRepositoryInfo, HacsNotSoBasicException

    custom_repository_list = {}
    custom_repository_list["integration"] = {}
    custom_repository_list["plugin"] = {}

    def __init__(self):
        """Set up a HacsRepoBase object."""
        self.additional_info = None
        self.content_files = []
        self.content_objects = None
        self.content_path = None
        self.custom = False
        self.description = None
        self.hide = False
        self.installed = False
        self.last_release_object = None
        self.last_release_tag = None
        self.last_updated = None
        self.name = None
        self.pending_restart = False
        self.pending_update = False
        self.ref = None
        self.releases = None
        self.repository = None
        self.repository_id = None
        self.repository_name = None
        self.repository_type = None
        self.track = False
        self.version_available = None
        self.version_installed = None


    def custom_repository_list_add(self):
        """Add repository to custom_repository_list."""


    def custom_repository_list_remove(self):
        """Add repository to custom_repository_list."""


    def validate_repository_name(self):
        """Validate the given repository_name."""
        if "/" not in self.repository_name:
            raise self.HacsRepositoryInfo(
                "GitHub repository name "
                f"'{self.repository_name}' is not the correct format")

        elif len(self.repository_name.split('/')) > 2:
            raise self.HacsRepositoryInfo(
                "GitHub repository name "
                f"'{self.repository_name}' is not the correct format")

    def set_repository(self):
        """Set the Github repository object."""
        if self.github is None:
            raise self.HacsRepositoryInfo("GitHub object is missing")
        elif self.repository_name is None:
            raise self.HacsRepositoryInfo("GitHub repository name is missing")

        try:
            # Assign to a temp var so we can check it before using it.
            temp = self.github.get_repo(self.repository_name)
            self.repository = temp

        except Exception as exception:
            _LOGGER.error(
                f"Failed to set repository object for '{self.repository_name}'"
                f" - Exception: {exception}")

    def set_repository_id(self):
        """Set the ID of an repository."""
        if self.github is None:
            raise self.HacsRepositoryInfo("GitHub object is missing")
        elif self.repository_name is None:
            raise self.HacsRepositoryInfo("GitHub repository name is missing")
        elif self.repository is None:
            raise self.HacsRepositoryInfo("GitHub repository object is missing")

        try:
            # Assign to a temp var so we can check it before using it.
            temp = self.repository.id

            if not isinstance(temp, int):
                raise TypeError(f"Value {temp} is not int Type.")
            self.repository_id = temp

        except Exception as exception:
            _LOGGER.error(
                f"Failed to set repository ID for '{self.repository_name}'"
                f" - Exception: {exception}")
