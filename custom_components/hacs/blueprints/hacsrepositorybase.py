"""Blueprint for HacsRepositoryBase."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except,wildcard-import
import logging

from custom_components.hacs.blueprints import HacsBase

_LOGGER = logging.getLogger(__name__)

class HacsRepositoryBase(HacsBase):
    """HacsRepoBase Class"""
    from custom_components.hacs.exceptions import HacsRepositoryInfo, HacsNotSoBasicException

    def __init__(self):
        """Set up a HacsRepoBase object."""
        self.additional_info = None
        self.content_files = None
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
        self.version_installed = None

    def log_repository_info(self):
        """Print current repository info in the log."""
        message = f"""
        Repository: {self.repository_name}
        Repository ref: {self.ref}
        Repository last update: {self.last_updated}
        Repository releases: {self.releases}
        Repository last release: {self.last_release_tag}
        Repository files: {self.content_files}
        """
        _LOGGER.debug(message)

    def set_additional_info(self):
        """Add additional info (from info.md)."""
        if self.repository is None:
            raise self.HacsRepositoryInfo("GitHub repository object is missing")
        elif self.ref is None:
            raise self.HacsRepositoryInfo("GitHub repository ref is missing")

        try:
            # Assign to a temp var so we can check it before using it.
            temp = self.repository.get_file_contents("info.md", self.ref)
            temp = temp.decoded_content.decode()
            self.additional_info = temp

        except Exception:
            # We kinda expect this one to fail
            pass

    def set_custom(self):
        """Set the custom flag."""
        # Check if we need to run this.
        if self.custom is not None:
            return

        if self.repository_name is None:
            raise self.HacsRepositoryInfo("GitHub repository name is missing")

        try:
            # Assign to a temp var so we can check it before using it.
            temp = self.repository_name

            temp = temp.split("/")[0]

            if temp in ["custom-components", "csutom-cards"]:
                self.custom = False
            else:
                self.custom = True

        except Exception as exception:
            _LOGGER.error(
                f"Failed to set custom flag for '{self.repository_name}'"
                f" - Exception: {exception}")

    def set_description(self):
        """Set the custom flag."""
        if self.repository is None:
            raise self.HacsRepositoryInfo("GitHub repository object is missing")

        try:
            # Assign to a temp var so we can check it before using it.
            temp = self.repository.description

            if temp is not None:
                self.description = temp
            else:
                self.description = ""

        except Exception as exception:
            _LOGGER.error(
                f"Failed to set repository description '{self.repository_name}'"
                f" - Exception: {exception}")

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

    def set_repository_releases(self):
        """Set attributes for releases."""
        if self.repository is None:
            raise self.HacsRepositoryInfo("GitHub repository object is missing")

        try:
            # Assign to a temp vars so we can check it before using it.
            temp = list(self.repository.get_releases())
            releases = []

            if temp:
                # Set info about the latest release.
                # Assign to a releasetemp var so we can check it before using it.
                releasetemp = temp[0]
                self.last_release_object = releasetemp
                self.last_release_tag = releasetemp.tag_name

                # Loop though the releases and add the .tag_name.
                for release in temp:
                    releases.append(release.tag_name)

                # Check if out temp actually have content.
                if releases:
                    self.releases = releases
                else:
                    raise self.HacsRepositoryInfo("Github releases are missing")

        except Exception as exception:
            _LOGGER.error(
                f"Failed to set repository relsease '{self.repository_name}'"
                f" - Exception: {exception}")

    def set_ref(self):
        """Set repository ref to use."""
        # Check if we need to run this.
        if self.ref is not None:
            return

        if self.repository is None:
            raise self.HacsRepositoryInfo("GitHub repository object is missing")

        try:
            # Assign to a temp vars so we can check it before using it.
            if self.last_release_tag is not None:
                temp = f"tags/{self.last_release_tag}"
            else:
                temp = self.repository.default_branch

            # We need this one so lets check it!
            if temp:
                if temp.count() < 1:
                    raise self.HacsRepositoryInfo(
                        f"GitHub repository ref is wrong {temp}")

                elif not isinstance(temp, str):
                    raise self.HacsRepositoryInfo(
                        f"GitHub repository ref is wrong {temp}")

                # Good! "tests" passed.
                else:
                    self.ref = temp

        except Exception as exception:
            _LOGGER.error(
                f"Failed to set repository relsease '{self.repository_name}'"
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

    def return_last_update(self):
        """Return a last update string."""
        if self.repository is None:
            raise self.HacsRepositoryInfo("GitHub repository object is missing")

        try:
            # Assign to a temp var so we can check it before using it.
            if self.last_release_tag is not None:
                temp = self.last_release_object.created_at
            else:
                temp = self.repository.updated_at

            temp = temp.strftime("%d %b %Y %H:%M:%S")

        except Exception as exception:
            _LOGGER.error(
                f"Failed to get last update for '{self.repository_name}'"
                f" - Exception: {exception}")
