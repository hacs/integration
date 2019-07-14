"""Blueprint for HacsRepositoryBase."""
# pylint: disable=too-many-instance-attributes,invalid-name,broad-except,wildcard-import,no-member
from asyncio import sleep
from datetime import datetime
import logging
import pathlib
import os
import shutil
from distutils.version import LooseVersion
from ..aiogithub.exceptions import AIOGitHubException
from ..hacsbase import HacsBase
from ..hacsbase.exceptions import (
    HacsRepositoryInfo,
    HacsUserScrewupException,
    HacsBaseException,
    HacsBlacklistException,
)
from ..handler.download import async_download_file, async_save_file
from ..hacsbase.const import VERSION, NOT_SUPPORTED_HA_VERSION

_LOGGER = logging.getLogger("custom_components.hacs.repository")


class HacsRepositoryBase(HacsBase):
    """HacsRepoBase Class"""

    def __init__(self):
        """Set up a HacsRepoBase object."""
        self.additional_info = None
        self.authors = None
        self.content_files = None
        self.content_objects = None
        self.content_path = None
        self.description = ""
        self.hide = False
        self.info = None
        self.installed = False
        self.installed_commit = None
        self.last_commit = None
        self.last_release_object = None
        self.last_release_tag = None
        self.last_updated = None
        self.homeassistant_version = None
        self.new = True
        self.pending_restart = False
        self.reasons = []
        self.releases = None
        self.repository = None
        self.repository_name = None
        self.repository_type = None
        self.repository_id = None
        self.published_tags = []
        self.selected_tag = None
        self.show_beta = False
        self.track = True
        self.topics = []
        self.updated_info = False
        self.version_installed = None

    @property
    def pending_update(self):
        """Return flag if the an update is pending."""
        if self.installed:
            if self.version_installed:
                return bool(self.last_release_tag != self.version_installed)
            else:
                return bool(self.installed_commit != self.last_commit)
        return False

    @property
    def custom(self):
        """Return flag if the repository is custom."""
        if self.repository_name.split("/")[0] in ["custom-components", "custom-cards"]:
            return False
        elif self.repository_name in self._default_repositories:
            return False
        return True

    @property
    def local_path(self):
        """Return local path."""
        local_path = None
        if self.repository_type == "appdaemon":
            local_path = "{}/appdaemon/apps/{}".format(self.config_dir, self.name)

        elif self.repository_type == "integration":
            if self.domain is None:
                local_path = None
            else:
                local_path = "{}/custom_components/{}".format(
                    self.config_dir, self.domain
                )

        elif self.repository_type == "plugin":
            local_path = "{}/www/community/{}".format(self.config_dir, self.name)

        elif self.repository_type == "python_script":
            local_path = "{}/python_scripts".format(self.config_dir)

        elif self.repository_type == "theme":
            local_path = "{}/themes".format(self.config_dir)

        return local_path

    @property
    def ref(self):
        """Return the repository ref."""
        if self.selected_tag is not None:
            if self.selected_tag == self.repository.default_branch:
                return self.repository.default_branch
            else:
                return "tags/{}".format(self.selected_tag)
        elif self.last_release_tag is not None:
            return "tags/{}".format(self.last_release_tag)
        return self.repository.default_branch

    @property
    def can_install(self):
        """Return bool if repository can be installed."""
        if self.homeassistant_version is not None:
            if self.version_or_commit == "version":
                if LooseVersion(self.store.ha_version) < LooseVersion(self.homeassistant_version):
                    return False
        return True

    @property
    def version_or_commit(self):
        """Does the repositoriy use releases or commits?"""
        if self.last_release_tag is not None:
            version_or_commit = "version"
        else:
            version_or_commit = "commit"
        return version_or_commit

    async def setup_repository(self):
        """
        Run initialation to setup a repository.

        Return True if everything is validated and ok.
        """
        # Check the blacklist
        if self.repository_name in self.blacklist or not self.track:
            raise HacsBlacklistException

        # Hide HACS
        if self.repository_name == "custom-components/hacs":
            self.hide = False
            self.installed = True
            self.version_installed = VERSION

        # Validate the repository name
        await self.validate_repository_name()

        # Update repository info
        await self.update()  # pylint: disable=no-member

    async def common_update(self):
        """Run common update tasks."""
        # Check the blacklist
        if self.repository_name in self.blacklist or not self.track:
            raise HacsBlacklistException

        # Set the Gihub repository object
        await self.set_repository()

        # Set latest commit sha
        await self.repository.set_last_commit()
        self.last_commit = self.repository.last_commit

        # Set repository releases
        await self.set_repository_releases()

        # Setlast updated.
        self.last_updated = await self.return_last_update()

        try:
            # Set additional info
            await self.set_additional_info()
            if self.additional_info is not None:
                info = await self.aiogithub.render_markdown(self.additional_info)
                info = info.replace("<h3>", "<h6>").replace("</h3>", "</h6>")
                info = info.replace("<h2>", "<h5>").replace("</h2>", "</h5>")
                info = info.replace("<h1>", "<h4>").replace("</h1>", "</h4>")
                info = info.replace("<code>", "<code class='codeinfo'>")
                info = info.replace(
                    '<a href="http', '<a rel="noreferrer" target="_blank" href="http'
                )
                info = info.replace("<ul>", "")
                info = info.replace("</ul>", "")
                self.additional_info = info
        except AIOGitHubException:
            self.additional_info = None

    async def download_repository_directory_content(
        self, repository_directory_path, local_directory, ref
    ):
        """Download the content of a directory."""
        try:
            # Get content
            if self.content_path == "release" or self.repository_type in [
                "python_script",
                "theme",
            ]:
                contents = self.content_objects
            else:
                contents = await self.repository.get_contents(
                    repository_directory_path, ref
                )

            for content_object in contents:
                if content_object.type == "dir" and self.content_path != "":
                    await self.download_repository_directory_content(
                        content_object.path, local_directory, ref
                    )
                    continue
                if (
                    self.repository_type == "plugin"
                    and not content_object.name.endswith(".js")
                    and self.content_path != "dist"
                ):
                    # For plugins we currently only need .js files
                    continue

                _LOGGER.debug("Downloading %s", content_object.name)

                filecontent = await async_download_file(
                    self.hass, content_object.download_url
                )

                if filecontent is None:
                    _LOGGER.debug(
                        "There was an error downloading the file %s",
                        content_object.name,
                    )
                    continue

                # Save the content of the file.
                if (
                    self.repository_type in ["python_script", "theme"]
                    or self.content_path == "release"
                ):
                    local_directory = self.local_path
                else:
                    _content_path = content_object.path
                    _content_path = _content_path.replace(
                        "{}/".format(self.content_path), ""
                    )

                    local_directory = "{}/{}".format(self.local_path, _content_path)
                    local_directory = local_directory.split(
                        "/{}".format(content_object.name)
                    )[0]

                # Check local directory
                pathlib.Path(local_directory).mkdir(parents=True, exist_ok=True)

                local_file_path = "{}/{}".format(local_directory, content_object.name)
                await async_save_file(local_file_path, filecontent)

        except Exception as exception:
            raise HacsBaseException(exception)

    async def install(self):
        """Run install tasks."""
        start_time = datetime.now()
        _LOGGER.info("(%s) - Starting installation", self.repository_name)
        try:
            if self.content_path == "release" and self.selected_tag == self.repository.default_branch:
                _LOGGER.error("Version %s can not be installed.", self.selected_tag)
                return

            # Run update
            await self.update()  # pylint: disable=no-member

            if not self.can_install:
                message = NOT_SUPPORTED_HA_VERSION.format(
                    self.ha_version,
                    self.last_release_tag,
                    self.name,
                    str(self.homeassistant_version),
                )
                _LOGGER.error(message)
                return False

            # Check local directory
            await self.check_local_directory()

            # Download files
            await self.download_repository_directory_content(
                self.content_path, self.local_path, self.ref
            )

        except HacsBaseException as exception:
            _LOGGER.debug("(%s) - %s", self.repository_name, exception)
            return False

        else:
            if self.selected_tag is not None:
                self.version_installed = self.selected_tag
            else:
                self.version_installed = self.last_release_tag
            self.installed = True
            self.installed_commit = self.last_commit
            if self.repository_type == "integration":
                self.pending_restart = True
            _LOGGER.info(
                "(%s) - installation completed in %s seconds",
                self.repository_name,
                (datetime.now() - start_time).seconds,
            )

        if self.repository_type == "integration":
            if self.config_flow:
                await self.reload_config_flows()

    async def remove(self):
        """Run remove tasks."""
        _LOGGER.debug("(%s) - Starting removal", self.repository_name)

        if self.repository_id in self.store.repositories:
            del self.store.repositories[self.repository_id]
        for repository in self.store.frontend:
            if repository.repository_id == self.repository_id:
                self.store.frontend.remove(repository)

    async def uninstall(self):
        """Run uninstall tasks."""
        _LOGGER.debug("(%s) - Starting uninstall", self.repository_name)
        await self.remove_local_directory()
        self.installed = False
        if self.repository_type == "integration":
            self.pending_restart = True
        self.version_installed = None

    async def check_local_directory(self, path=None):
        """Check the local directory."""
        try:
            if path is not None:
                local_path = path
            else:
                local_path = self.local_path

            # Remove if it's allready there.
            if os.path.exists(local_path):
                await self.remove_local_directory()

            # Create the new directory
            _LOGGER.debug("(%s) - Creating %s", self.repository_name, local_path)
            pathlib.Path(local_path).mkdir(parents=True, exist_ok=True)

        except Exception as exception:
            _LOGGER.debug(
                "(%s) - Creating directory %s failed with %s",
                self.repository_name,
                local_path,
                exception,
            )
            return

    async def remove_local_directory(self):
        """Check the local directory."""
        try:
            if self.repository_type == "python_script":
                local_path = "{}/{}.py".format(self.local_path, self.name)
            elif self.repository_type == "theme":
                local_path = "{}/{}.yaml".format(self.local_path, self.name)
            else:
                local_path = self.local_path

            if os.path.exists(local_path):
                _LOGGER.debug("(%s) - Removing %s", self.repository_name, local_path)

                if self.repository_type in ["python_script", "theme"]:
                    os.remove(local_path)
                else:
                    shutil.rmtree(local_path)

                while os.path.exists(local_path):
                    await sleep(1)

        except Exception as exception:
            _LOGGER.debug(
                "(%s) - Removing %s failed with %s",
                self.repository_name,
                local_path,
                exception,
            )
            return

    async def set_additional_info(self):
        """Add additional info (from info.md)."""
        from ..handler.template import render_template
        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")
        elif self.ref is None:
            raise HacsRepositoryInfo("GitHub repository ref is missing")

        # Looking for info file
        info = None
        info_files = ["info", "info.md"]
        root = await self.repository.get_contents("", self.ref)
        for file in root:
            if file.name.lower() in info_files:
                info = await self.repository.get_contents(file.name, self.ref)
                break
        if info is None:
            self.additional_info = ""
        else:
            self.additional_info = render_template(info.content, self)

    async def set_repository(self):
        """Set the AIOGitHub repository object."""
        self.repository = await self.aiogithub.get_repo(self.repository_name)
        self.last_commit = self.repository.last_commit
        self.repository_id = str(self.repository.id)
        self.description = self.repository.description
        self.topics = self.repository.topics

    async def set_repository_releases(self):
        """Set attributes for releases."""
        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")

        # Assign to a temp vars so we can check it before using it.
        if self.show_beta:
            temp = await self.repository.get_releases(prerelease=True)
        else:
            temp = await self.repository.get_releases(prerelease=False)

        if not temp:
            return

        self.published_tags = []

        for release in temp:
            self.published_tags.append(release.tag_name)

        self.last_release_object = temp[0]
        if self.selected_tag is not None:
            if self.selected_tag != self.repository.default_branch:
                for release in temp:
                    if release.tag_name == self.selected_tag:
                        self.last_release_object = release
                        break
        self.last_release_tag = temp[0].tag_name

    async def validate_repository_name(self):
        """Validate the given repository_name."""
        if "/" not in self.repository_name:
            raise HacsUserScrewupException(
                "GitHub repository name "
                "'{}' is not the correct format".format(self.repository_name)
            )

        elif len(self.repository_name.split("/")) > 2:
            raise HacsUserScrewupException(
                "GitHub repository name "
                "'{}' is not the correct format".format(self.repository_name)
            )

    async def return_last_update(self):
        """Return a last update string."""
        if self.repository is None:
            raise HacsRepositoryInfo("GitHub repository object is missing")

        # Assign to a temp var so we can check it before using it.
        if self.last_release_tag is not None:
            temp = self.last_release_object.published_at
        else:
            temp = self.repository.pushed_at

        return temp.strftime("%d %b %Y %H:%M")


