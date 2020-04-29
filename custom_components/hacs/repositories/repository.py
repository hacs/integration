"""Repository."""
# pylint: disable=broad-except, bad-continuation, no-member
import json
import os
import tempfile
import zipfile
from integrationhelper import Validate
from aiogithubapi import AIOGitHubException
from .manifest import HacsManifest
from ..helpers.misc import get_repository_name
from ..handler.download import async_download_file, async_save_file
from ..helpers.misc import version_left_higher_then_right
from ..helpers.install import install_repository, version_to_install

from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.globals import get_hacs
from custom_components.hacs.helpers.information import (
    get_info_md_content,
    get_repository,
)
from custom_components.hacs.helpers.validate_repository import (
    common_validate,
    common_update_data,
)
from custom_components.hacs.repositories.repositorydata import RepositoryData


class RepositoryVersions:
    """Versions."""

    available = None
    available_commit = None
    installed = None
    installed_commit = None


class RepositoryStatus:
    """Repository status."""

    hide = False
    installed = False
    last_updated = None
    new = True
    selected_tag = None
    show_beta = False
    track = True
    updated_info = False
    first_install = True


class RepositoryInformation:
    """RepositoryInformation."""

    additional_info = None
    authors = []
    category = None
    default_branch = None
    description = ""
    state = None
    full_name = None
    file_name = None
    javascript_type = None
    homeassistant_version = None
    last_updated = None
    uid = None
    stars = 0
    info = None
    name = None
    topics = []


class RepositoryReleases:
    """RepositoyReleases."""

    last_release = None
    last_release_object = None
    last_release_object_downloads = None
    published_tags = []
    objects = []
    releases = False
    downloads = None


class RepositoryPath:
    """RepositoryPath."""

    local = None
    remote = None


class RepositoryContent:
    """RepositoryContent."""

    path = None
    files = []
    objects = []
    single = False


class HacsRepository:
    """HacsRepository."""

    def __init__(self):
        """Set up HacsRepository."""
        self.hacs = get_hacs()
        self.data = RepositoryData()
        self.content = RepositoryContent()
        self.content.path = RepositoryPath()
        self.information = RepositoryInformation()
        self.repository_object = None
        self.status = RepositoryStatus()
        self.state = None
        self.force_branch = False
        self.integration_manifest = {}
        self.repository_manifest = HacsManifest.from_dict({})
        self.validate = Validate()
        self.releases = RepositoryReleases()
        self.versions = RepositoryVersions()
        self.pending_restart = False
        self.tree = []
        self.treefiles = []
        self.ref = None

    @property
    def pending_upgrade(self):
        """Return pending upgrade."""
        if not self.can_install:
            return False
        if self.status.installed:
            if self.status.selected_tag is not None:
                if self.status.selected_tag == self.data.default_branch:
                    if self.versions.installed_commit != self.versions.available_commit:
                        return True
                    return False
            if self.display_installed_version != self.display_available_version:
                return True
        return False

    @property
    def config_flow(self):
        """Return bool if integration has config_flow."""
        if self.integration_manifest:
            if self.data.full_name == "hacs/integration":
                return False
            return self.integration_manifest.get("config_flow", False)
        return False

    @property
    def custom(self):
        """Return flag if the repository is custom."""
        if self.data.full_name.split("/")[0] in ["custom-components", "custom-cards"]:
            return False
        if self.data.full_name.lower() in [x.lower() for x in self.hacs.common.default]:
            return False
        if self.data.full_name == "hacs/integration":
            return False
        return True

    @property
    def can_install(self):
        """Return bool if repository can be installed."""
        target = None
        if self.information.homeassistant_version is not None:
            target = self.information.homeassistant_version
        if self.repository_manifest is not None:
            if self.data.homeassistant is not None:
                target = self.data.homeassistant

        if target is not None:
            if self.releases.releases:
                if not version_left_higher_then_right(
                    self.hacs.system.ha_version, target
                ):
                    return False
        return True

    @property
    def display_name(self):
        """Return display name."""
        return get_repository_name(self)

    @property
    def display_status(self):
        """Return display_status."""
        if self.status.new:
            status = "new"
        elif self.pending_restart:
            status = "pending-restart"
        elif self.pending_upgrade:
            status = "pending-upgrade"
        elif self.status.installed:
            status = "installed"
        else:
            status = "default"
        return status

    @property
    def display_status_description(self):
        """Return display_status_description."""
        description = {
            "default": "Not installed.",
            "pending-restart": "Restart pending.",
            "pending-upgrade": "Upgrade pending.",
            "installed": "No action required.",
            "new": "This is a newly added repository.",
        }
        return description[self.display_status]

    @property
    def display_installed_version(self):
        """Return display_authors"""
        if self.versions.installed is not None:
            installed = self.versions.installed
        else:
            if self.versions.installed_commit is not None:
                installed = self.versions.installed_commit
            else:
                installed = ""
        return installed

    @property
    def display_available_version(self):
        """Return display_authors"""
        if self.versions.available is not None:
            available = self.versions.available
        else:
            if self.versions.available_commit is not None:
                available = self.versions.available_commit
            else:
                available = ""
        return available

    @property
    def display_version_or_commit(self):
        """Does the repositoriy use releases or commits?"""
        if self.releases.releases:
            version_or_commit = "version"
        else:
            version_or_commit = "commit"
        return version_or_commit

    @property
    def main_action(self):
        """Return the main action."""
        actions = {
            "new": "INSTALL",
            "default": "INSTALL",
            "installed": "REINSTALL",
            "pending-restart": "REINSTALL",
            "pending-upgrade": "UPGRADE",
        }
        return actions[self.display_status]

    async def common_validate(self):
        """Common validation steps of the repository."""
        await common_validate(self)

    async def common_registration(self):
        """Common registration steps of the repository."""
        # Attach repository
        if self.repository_object is None:
            self.repository_object = await get_repository(
                self.hacs.session, self.hacs.configuration.token, self.data.full_name
            )
            self.data.update_data(self.repository_object.attributes)

        # Set id
        self.information.uid = str(self.data.id)

        # Set topics
        self.data.topics = self.data.topics

        # Set stargazers_count
        self.data.stargazers_count = self.data.stargazers_count

        # Set description
        self.data.description = self.data.description

        if self.hacs.action:
            if self.data.description is None or len(self.data.description) == 0:
                raise HacsException("Missing repository description")

    async def common_update(self):
        """Common information update steps of the repository."""
        self.logger.debug("Getting repository information")

        # Attach repository
        await common_update_data(self)

        # Update last updaeted
        self.information.last_updated = self.repository_object.attributes.get(
            "pushed_at", 0
        )

        # Update last available commit
        await self.repository_object.set_last_commit()
        self.versions.available_commit = self.repository_object.last_commit

        # Get the content of hacs.json
        await self.get_repository_manifest_content()

        # Update "info.md"
        self.information.additional_info = await get_info_md_content(self)

    async def install(self):
        """Common installation steps of the repository."""
        await install_repository(self)

    async def download_zip(self, validate):
        """Download ZIP archive from repository release."""
        try:
            contents = False

            for release in self.releases.objects:
                self.logger.info(f"ref: {self.ref}  ---  tag: {release.tag_name}")
                if release.tag_name == self.ref.split("/")[1]:
                    contents = release.assets

            if not contents:
                return validate

            for content in contents or []:
                filecontent = await async_download_file(content.download_url)

                if filecontent is None:
                    validate.errors.append(f"[{content.name}] was not downloaded.")
                    continue

                result = await async_save_file(
                    f"{tempfile.gettempdir()}/{self.data.filename}", filecontent
                )
                with zipfile.ZipFile(
                    f"{tempfile.gettempdir()}/{self.data.filename}", "r"
                ) as zip_file:
                    zip_file.extractall(self.content.path.local)

                if result:
                    self.logger.info(f"download of {content.name} complete")
                    continue
                validate.errors.append(f"[{content.name}] was not downloaded.")
        except Exception:
            validate.errors.append(f"Download was not complete.")

        return validate

    async def download_content(self, validate, directory_path, local_directory, ref):
        """Download the content of a directory."""
        from custom_components.hacs.helpers.download import download_content

        validate = await download_content(self)
        return validate

    async def get_repository_manifest_content(self):
        """Get the content of the hacs.json file."""
        if not "hacs.json" in [x.filename for x in self.tree]:
            if self.hacs.action:
                raise HacsException("No hacs.json file in the root of the repository.")
            return
        if self.hacs.action:
            self.logger.debug("Found hacs.json")

        if self.ref is None:
            self.ref = version_to_install(self)
        try:
            manifest = await self.repository_object.get_contents("hacs.json", self.ref)
            self.repository_manifest = HacsManifest.from_dict(
                json.loads(manifest.content)
            )
            self.data.update_data(json.loads(manifest.content))
        except (AIOGitHubException, Exception) as exception:  # Gotta Catch 'Em All
            if self.hacs.action:
                raise HacsException(f"hacs.json file is not valid ({exception}).")
        if self.hacs.action:
            self.logger.debug("hacs.json is valid")

    def remove(self):
        """Run remove tasks."""
        self.logger.info("Starting removal")

        if self.information.uid in self.hacs.common.installed:
            self.hacs.common.installed.remove(self.information.uid)
        for repository in self.hacs.repositories:
            if repository.information.uid == self.information.uid:
                self.hacs.repositories.remove(repository)

    async def uninstall(self):
        """Run uninstall tasks."""
        self.logger.info("Uninstalling")
        if not await self.remove_local_directory():
            raise HacsException("Could not uninstall")
        self.status.installed = False
        if self.data.category == "integration":
            if self.config_flow:
                await self.reload_custom_components()
            else:
                self.pending_restart = True
        elif self.data.category == "theme":
            try:
                await self.hacs.hass.services.async_call(
                    "frontend", "reload_themes", {}
                )
            except Exception:  # pylint: disable=broad-except
                pass
        if self.data.full_name in self.hacs.common.installed:
            self.hacs.common.installed.remove(self.data.full_name)
        self.versions.installed = None
        self.versions.installed_commit = None
        self.hacs.hass.bus.async_fire(
            "hacs/repository",
            {"id": 1337, "action": "uninstall", "repository": self.data.full_name},
        )

    async def remove_local_directory(self):
        """Check the local directory."""
        import shutil
        from asyncio import sleep

        try:
            if self.data.category == "python_script":
                local_path = "{}/{}.py".format(self.content.path.local, self.data.name)
            elif self.data.category == "theme":
                if os.path.exists(
                    f"{self.hacs.system.config_path}/{self.hacs.configuration.theme_path}/{self.data.name}.yaml"
                ):
                    os.remove(
                        f"{self.hacs.system.config_path}/{self.hacs.configuration.theme_path}/{self.data.name}.yaml"
                    )
                local_path = self.content.path.local
            elif self.data.category == "integration":
                if not self.data.domain:
                    self.logger.error("Missing domain")
                    return False
                local_path = self.content.path.local
            else:
                local_path = self.content.path.local

            if os.path.exists(local_path):
                self.logger.debug(f"Removing {local_path}")

                if self.data.category in ["python_script"]:
                    os.remove(local_path)
                else:
                    shutil.rmtree(local_path)

                while os.path.exists(local_path):
                    await sleep(1)

        except Exception as exception:
            self.logger.debug(f"Removing {local_path} failed with {exception}")
            return False
        return True
