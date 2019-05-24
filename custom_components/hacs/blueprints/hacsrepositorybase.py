"""Blueprint for HacsRepositoryBase."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except
from asyncio import sleep
import logging

from custom_components.hacs.blueprints import HacsBase

_LOGGER = logging.getLogger(__name__)

class HacsRepositoryBase(HacsBase):
    """HacsRepoBase Class"""
    from custom_components.hacs.exceptions import HacsRepositoryInfo

    custom_repository_list = {}
    custom_repository_list["integration"] = {}
    custom_repository_list["plugin"] = {}

    def __init__(self):
        """Set up a HacsRepoBase object."""
        self._additional_info = None
        self._content_files = []
        self._content_objects = None
        self._content_path = None
        self._description = None
        self._hide = False
        self._installed = False
        self._last_updated = None
        self._name = None
        self._pending_restart = False
        self._pending_update = False
        self._releases = None
        self._repository = None
        self._repository_id = None
        self._repository_type = None
        self._repository_name = None
        self._track = False
        self._version_available = None
        self._version_installed = None

        self.github_ref = None
        self.github_last_release = None # ok

    @property
    def description(self):
        """
        Repository description.

        Retruns a string with the description of the repository if there is one,
        if not it returns a blank string ("")
        """
        return "" if self._description is None else self._description

    @property
    def repository(self):
        """
        Repository object.

        Retruns a Github Repository object.
        """
        return self._repository

    @property
    def repository_name(self):
        """
        Repository name.

        Retruns a string with the full name of the repository (USER/REPO),

        example: "awesome-developer/awesome-repo"
        """
        return self._repository_name



    def custom_repository_list_add(self):
        """Add repository to custom_repository_list."""


    def custom_repository_list_remove(self):
        """Add repository to custom_repository_list."""

    def set_repository_id(self):
        """Set the ID of an repository."""
        if self.github is None:
            raise self.HacsRepositoryInfo("GitHub object is missing")
        elif self.repository_name is None:
            raise self.HacsRepositoryInfo("GitHub repository name is missing")
        elif self.repository is None:
            raise self.HacsRepositoryInfo("GitHub repository object is missing")

        try:
            temp = self.repository.id

            if not isinstance(temp, int):
                raise TypeError(f"Value {temp} is not int Type.")
            self._repository_id = temp
        except Exception as exception:
            _LOGGER.error(
                f"Failed to set repository ID for '{self.repository_name}'"
                f" - Exception: {exception}")

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
