"""Repository."""
# pylint: disable=broad-except
from integrationhelper import Validate, Logger
from ..hacsbase import Hacs


RERPOSITORY_CLASSES = {}


def register_repository_class(cls):
    """Register class."""
    RERPOSITORY_CLASSES[cls.category] = cls
    return cls


class RepositoryVersions:
    """Versions."""

    available = None
    available_commit = None
    installed = None
    installed_commit = None


class PendingActions:
    """Pending actions."""

    restart = False

    @property
    def upgrade(self):
        """Return bool if benting upgrade."""


class RepositoryStatus:
    """Repository status."""

    actions = PendingActions()
    hide = False
    installed = False
    last_updated = None
    new = True
    selected_tag = None
    show_beta = False
    track = True
    updated_info = False


class RepositoryInformation:
    """RepositoryInformation."""

    additional_info = None
    authors = []
    category = None
    default_branch = None
    description = ""
    full_name = None
    homeassistant_version = None
    uid = None
    info = None
    local_path = None
    name = None
    remote_path = None
    topics = []


class RepositoryReleases:
    """RepositoyReleases."""

    last_release = None
    last_release_object = None
    published_tags = []
    releases = False


class RepositoryContent:
    """RepositoryContent."""

    files = []
    objects = []


class HacsRepository(Hacs):
    """HacsRepository."""

    def __init__(self):
        """Set up HacsRepository."""

        self.content = RepositoryContent()
        self.information = RepositoryInformation()
        self.repository_object = None
        self.status = RepositoryStatus()
        self.validate = None
        self.versions = RepositoryVersions()
        self.logger = None

    async def common_validate(self):
        """Common validation steps of the repository."""
        # Attach helpers
        self.validate = Validate()
        self.logger = Logger(
            f"hacs.repository.{self.information.category}.{self.information.full_name}"
        )

        # Step 1: Make sure the repository exist.
        self.logger.debug("Checking repository.")
        try:
            self.repository_object = await self.github.get_repo(
                self.information.full_name
            )
        except SystemError as exception:  # Gotta Catch 'Em All
            if not self.common.status.startup:
                self.logger.error(exception)
            self.validate.errors.append(
                f"Repository {self.information.full_name} does not exist."
            )
            return

    async def common_registration(self):
        """Common registration steps of the repository."""
        # Attach logger
        if self.logger is None:
            self.logger = Logger(
                f"hacs.repository.{self.information.category}.{self.information.full_name}"
            )
        # Attach repository
        if self.repository_object is None:
            self.repository_object = await self.github.get_repo(
                self.information.full_name
            )

        # Set values
        ## Set repository name
        self.information.name = self.information.full_name.split("/")[1]

        ## Set id
        self.information.uid = str(self.repository_object.id)

    async def common_update(self):
        """Common information update steps of the repository."""

    async def common_install(self):
        """Common installation steps of the repository."""
