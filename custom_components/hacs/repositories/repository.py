"""Repository."""
from integrationhelper import Validate
from ..hacsbase import Hacs


RERPOSITORY_CLASSES = {}


def register_repository_class(cls):
    """Register class."""
    RERPOSITORY_CLASSES[cls.name] = cls
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
    id = None
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
        self.validate = Validate()
        self.versions = RepositoryVersions()

    async def common_validate(self):
        """Common validation steps of the repository."""
        self.validate = Validate()

    async def common_update(self):
        """Common information update steps of the repository."""

    async def common_install(self):
        """Common installation steps of the repository."""
