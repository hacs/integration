"""Repository."""
# pylint: disable=broad-except, bad-continuation, no-member
from distutils.version import LooseVersion
from integrationhelper import Validate, Logger
from ..hacsbase import Hacs
from ..hacsbase.backup import Backup


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

    pending = PendingActions()
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
        self.releases = RepositoryReleases()
        self.versions = RepositoryVersions()
        self.logger = None

    @property
    def ref(self):
        """Return the ref."""
        if self.status.selected_tag is not None:
            if self.status.selected_tag == self.information.default_branch:
                return self.information.default_branch
            return "tags/{}".format(self.status.selected_tag)

        if self.releases.releases:
            return "tags/{}".format(self.versions.available)

        return self.information.default_branch

    @property
    def custom(self):
        """Return flag if the repository is custom."""
        if self.information.full_name.split("/")[0] in [
            "custom-components",
            "custom-cards",
        ]:
            return False
        if self.information.full_name in self.common.default:
            return False
        return True

    @property
    def can_install(self):
        """Return bool if repository can be installed."""
        if self.information.homeassistant_version is not None:
            if self.releases.releases:
                if LooseVersion(self.system.ha_version) < LooseVersion(
                    self.information.homeassistant_version
                ):
                    return False
        return True

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
        except Exception as exception:  # Gotta Catch 'Em All
            if not self.common.status.startup:
                self.logger.error(exception)
            self.validate.errors.append("Repository does not exist.")
            return

        # Step 2: Make sure the repository is not archived.
        if self.repository_object.archived:
            self.validate.errors.append("Repository is archived.")
            return

        # Step 3: Make sure the repository is not in the blacklist.
        if self.information.full_name in self.common.blacklist:
            self.validate.errors.append("Repository is in the blacklist.")
            return

        # Step 4: Get releases.
        await self.get_releases()

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

        # Set repository name
        self.information.name = self.information.full_name.split("/")[1]

        # Set id
        self.information.uid = str(self.repository_object.id)

        # Set topics
        self.information.topics = self.repository_object.topics

        # Set description
        if self.repository_object.description:
            self.information.description = self.repository_object.description

        # Get releases
        await self.get_releases()

    async def common_update(self):
        """Common information update steps of the repository."""
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

        # Update description
        if self.repository_object.description:
            self.information.description = self.repository_object.description

        # Update default branch
        self.information.default_branch = self.repository_object.default_branch

        # Update last available commit
        self.versions.available_commit = self.repository_object.last_commit

        # Update topics
        self.information.topics = self.repository_object.topics

        # Update "info.md"
        await self.get_info_md_content()

        # Update releases
        await self.get_releases()

    async def common_install(self):
        """Common installation steps of the repository."""
        validate = Validate()
        if self.status.installed:
            backup = Backup(self.information.local_path)
            backup.create()

        validate = await self.download_content(validate)

        if validate.errors:
            for error in validate.errors:
                self.logger.error(error)
            if self.status.installed:
                backup.restore()

        if self.status.installed:
            backup.cleanup()

        if validate.success:
            self.status.installed = True
            self.versions.installed_commit = self.versions.available_commit

            if self.status.selected_tag is not None:
                self.versions.installed = self.status.selected_tag
            else:
                self.versions.installed = self.versions.available

            if self.information.category == "integration":
                if self.config_flow:
                    await self.reload_config_flows()
                else:
                    self.status.pending.restart = True

    async def get_info_md_content(self):
        """Get the content of info.md"""
        from ..handler.template import render_template

        info_files = ["info", "info.md"]
        try:
            root = await self.repository_object.get_contents("", self.ref)
            for file in root:
                if file.name.lower() in info_files:
                    info = await self.repository_object.get_contents(
                        file.name, self.ref
                    )
                    break
            if info is None:
                self.information.additional_info = ""
            else:
                info = info.content
                info = info.replace("<h3>", "<h6>").replace("</h3>", "</h6>")
                info = info.replace("<h2>", "<h5>").replace("</h2>", "</h5>")
                info = info.replace("<h1>", "<h4>").replace("</h1>", "</h4>")
                info = info.replace("<code>", "<code class='codeinfo'>")
                info = info.replace(
                    '<a href="http', '<a rel="noreferrer" target="_blank" href="http'
                )
                info = info.replace("<ul>", "")
                info = info.replace("</ul>", "")
                self.information.additional_info = render_template(info, self)

        except Exception:  # Gotta Catch 'Em All
            return

    async def get_releases(self):
        """Get repository releases."""
        if self.status.show_beta:
            temp = await self.repository_object.get_releases(prerelease=True)
        else:
            temp = await self.repository_object.get_releases(prerelease=False)

        if not temp:
            return

        self.releases.published_tags = []

        for release in temp:
            self.releases.published_tags.append(release.tag_name)

        self.releases.last_release_object = temp[0]
        if self.status.selected_tag is not None:
            if self.status.selected_tag != self.information.default_branch:
                for release in temp:
                    if release.tag_name == self.status.selected_tag:
                        self.releases.last_release_object = release
                        break
        self.versions.available = temp[0].tag_name

    async def download_content(self, validate):
        """Download repository content."""
        remote = []
        local = []

        for item in remote:
            if item not in local:
                validate.errors.append(f"{item} not downloaded.")

        return validate
