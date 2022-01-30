"""Repository."""
from __future__ import annotations

from asyncio import sleep
from datetime import datetime
import json
import os
import pathlib
import shutil
import tempfile
from typing import TYPE_CHECKING, Any, List, Optional
import zipfile

from aiogithubapi import AIOGitHubAPIException, AIOGitHubAPINotModifiedException, GitHub
from aiogithubapi.const import ACCEPT_HEADERS
from aiogithubapi.objects.repository import AIOGitHubAPIRepository
import attr
from homeassistant.helpers.json import JSONEncoder

from ..enums import RepositoryFile
from ..exceptions import (
    HacsException,
    HacsNotModifiedException,
    HacsRepositoryArchivedException,
    HacsRepositoryExistException,
)
from ..utils.backup import Backup, BackupNetDaemon
from ..utils.decode import decode_content
from ..utils.decorator import concurrent
from ..utils.filters import filter_content_return_one_of_type
from ..utils.logger import get_hacs_logger
from ..utils.path import is_safe
from ..utils.queue_manager import QueueManager
from ..utils.store import async_remove_store
from ..utils.template import render_template
from ..utils.validate import Validate
from ..utils.version import (
    version_left_higher_or_equal_then_right,
    version_left_higher_then_right,
    version_to_download,
)
from ..utils.workarounds import DOMAIN_OVERRIDES

if TYPE_CHECKING:
    from ..base import HacsBase


class FileInformation:
    """FileInformation."""

    def __init__(self, url, path, name):
        self.download_url = url
        self.path = path
        self.name = name


@attr.s(auto_attribs=True)
class RepositoryData:
    """RepositoryData class."""

    archived: bool = False
    authors: List[str] = []
    category: str = ""
    content_in_root: bool = False
    country: List[str] = []
    config_flow: bool = False
    default_branch: str = None
    description: str = ""
    domain: str = ""
    domains: List[str] = []
    downloads: int = 0
    etag_repository: str = None
    file_name: str = ""
    filename: str = ""
    first_install: bool = False
    fork: bool = False
    full_name: str = ""
    hacs: str = None  # Minimum HACS version
    hide: bool = False
    hide_default_branch: bool = False
    homeassistant: str = None  # Minimum Home Assistant version
    id: int = 0
    iot_class: str = None
    installed: bool = False
    installed_commit: str = None
    installed_version: str = None
    open_issues: int = 0
    last_commit: str = None
    last_version: str = None
    last_updated: str = 0
    manifest_name: str = None
    new: bool = True
    last_fetched: datetime = None
    persistent_directory: str = None
    pushed_at: str = ""
    releases: bool = False
    render_readme: bool = False
    published_tags: List[str] = []
    selected_tag: str = None
    show_beta: bool = False
    stargazers_count: int = 0
    topics: List[str] = []
    zip_release: bool = False
    _storage_data: Optional[dict] = None

    @property
    def stars(self):
        """Return the stargazers count."""
        return self.stargazers_count or 0

    @property
    def name(self):
        """Return the name."""
        if self.category in ["integration", "netdaemon"]:
            return self.domain
        return self.full_name.split("/")[-1]

    def to_json(self):
        """Export to json."""
        return attr.asdict(
            self,
            filter=lambda attr, _: attr.name != "_storage_data" and attr.name != "last_fetched",
        )

    def memorize_storage(self, data) -> None:
        """Memorize the storage data."""
        self._storage_data = data

    def export_data(self) -> Optional[dict]:
        """Export to json if the data has changed.

        Returns the data to export if the data needs
        to be written.

        Returns None if the data has not changed.
        """
        export = json.loads(json.dumps(self.to_json(), cls=JSONEncoder))
        return None if self._storage_data == export else export

    @staticmethod
    def create_from_dict(source: dict):
        """Set attributes from dicts."""
        data = RepositoryData()
        for key in source:
            if key not in data.__dict__:
                continue
            if key == "pushed_at":
                if source[key] == "":
                    continue
                if "Z" in source[key]:
                    setattr(
                        data,
                        key,
                        datetime.strptime(source[key], "%Y-%m-%dT%H:%M:%SZ"),
                    )
                else:
                    setattr(
                        data,
                        key,
                        datetime.strptime(source[key], "%Y-%m-%dT%H:%M:%S"),
                    )
            elif key == "id":
                setattr(data, key, str(source[key]))
            elif key == "country":
                if isinstance(source[key], str):
                    setattr(data, key, [source[key]])
                else:
                    setattr(data, key, source[key])
            else:
                setattr(data, key, source[key])
        return data

    def update_data(self, data: dict):
        """Update data of the repository."""
        for key in data:
            if key not in self.__dict__:
                continue
            if key == "pushed_at":
                if data[key] == "":
                    continue
                if "Z" in data[key]:
                    setattr(
                        self,
                        key,
                        datetime.strptime(data[key], "%Y-%m-%dT%H:%M:%SZ"),
                    )
                else:
                    setattr(self, key, datetime.strptime(data[key], "%Y-%m-%dT%H:%M:%S"))
            elif key == "id":
                setattr(self, key, str(data[key]))
            elif key == "country":
                if isinstance(data[key], str):
                    setattr(self, key, [data[key]])
                else:
                    setattr(self, key, data[key])
            else:
                setattr(self, key, data[key])


@attr.s(auto_attribs=True)
class HacsManifest:
    """HacsManifest class."""

    name: str = None
    content_in_root: bool = False
    zip_release: bool = False
    filename: str = None
    manifest: dict = {}
    hacs: str = None
    hide_default_branch: bool = False
    domains: List[str] = []
    country: List[str] = []
    homeassistant: str = None
    persistent_directory: str = None
    iot_class: str = None
    render_readme: bool = False

    def to_dict(self):
        """Export to json."""
        return attr.asdict(self)

    @staticmethod
    def from_dict(manifest: dict):
        """Set attributes from dicts."""
        if manifest is None:
            raise HacsException("Missing manifest data")

        manifest_data = HacsManifest()

        manifest_data.manifest = manifest

        if country := manifest.get("country"):
            if isinstance(country, str):
                manifest["country"] = [country]

        for key in manifest:
            setattr(manifest_data, key, manifest[key])
        return manifest_data


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

    def __init__(self, hacs: HacsBase) -> None:
        """Set up HacsRepository."""
        self.hacs = hacs
        self.additional_info = ""
        self.data = RepositoryData()
        self.content = RepositoryContent()
        self.content.path = RepositoryPath()
        self.repository_object: AIOGitHubAPIRepository | None = None
        self.status = RepositoryStatus()
        self.state = None
        self.force_branch = False
        self.integration_manifest = {}
        self.repository_manifest = HacsManifest.from_dict({})
        self.validate = Validate()
        self.releases = RepositoryReleases()
        self.pending_restart = False
        self.tree = []
        self.treefiles = []
        self.ref = None
        self.logger = get_hacs_logger()

    def __str__(self) -> str:
        """Return a string representation of the repository."""
        return f"<{self.data.category.title()} {self.data.full_name}>"

    @property
    def display_name(self) -> str:
        """Return display name."""
        if self.repository_manifest.name is not None:
            return self.repository_manifest.name

        if self.data.category == "integration":
            if self.integration_manifest:
                if "name" in self.integration_manifest:
                    return self.integration_manifest["name"]

        return self.data.full_name.split("/")[-1].replace("-", " ").replace("_", " ").title()

    @property
    def ignored_by_country_configuration(self) -> bool:
        """Return True if hidden by country."""
        if self.data.installed:
            return False
        configuration = self.hacs.configuration.country.lower()
        manifest = [entry.lower() for entry in self.repository_manifest.country or []]
        if configuration == "all":
            return False
        if not manifest:
            return False
        return configuration not in manifest

    @property
    def display_status(self) -> str:
        """Return display_status."""
        if self.data.new:
            status = "new"
        elif self.pending_restart:
            status = "pending-restart"
        elif self.pending_update:
            status = "pending-upgrade"
        elif self.data.installed:
            status = "installed"
        else:
            status = "default"
        return status

    @property
    def display_status_description(self) -> str:
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
    def display_installed_version(self) -> str:
        """Return display_authors"""
        if self.data.installed_version is not None:
            installed = self.data.installed_version
        else:
            if self.data.installed_commit is not None:
                installed = self.data.installed_commit
            else:
                installed = ""
        return str(installed)

    @property
    def display_available_version(self) -> str:
        """Return display_authors"""
        if self.data.last_version is not None:
            available = self.data.last_version
        else:
            if self.data.last_commit is not None:
                available = self.data.last_commit
            else:
                available = ""
        return str(available)

    @property
    def display_version_or_commit(self) -> str:
        """Does the repositoriy use releases or commits?"""
        if self.data.releases:
            version_or_commit = "version"
        else:
            version_or_commit = "commit"
        return version_or_commit

    @property
    def main_action(self) -> str:
        """Return the main action."""
        actions = {
            "new": "INSTALL",
            "default": "INSTALL",
            "installed": "REINSTALL",
            "pending-restart": "REINSTALL",
            "pending-upgrade": "UPGRADE",
        }
        return actions[self.display_status]

    @property
    def pending_update(self) -> bool:
        """Return True if pending update."""
        if not self.can_download:
            return False
        if self.data.installed:
            if self.data.selected_tag is not None:
                if self.data.selected_tag == self.data.default_branch:
                    if self.data.installed_commit != self.data.last_commit:
                        return True
                    return False
            if self.display_version_or_commit == "version":
                if (
                    result := version_left_higher_then_right(
                        self.display_available_version,
                        self.display_installed_version,
                    )
                ) is not None:
                    return result
            if self.display_installed_version != self.display_available_version:
                return True

        return False

    @property
    def can_download(self) -> bool:
        """Return True if we can download."""
        if self.data.homeassistant is not None:
            if self.data.releases:
                if not version_left_higher_or_equal_then_right(
                    self.hacs.core.ha_version.string,
                    self.data.homeassistant,
                ):
                    return False
        return True

    @property
    def localpath(self) -> str | None:
        """Return localpath."""
        return None

    @property
    def should_try_releases(self) -> bool:
        """Return a boolean indicating whether to download releases or not."""
        if self.data.zip_release:
            if self.data.filename.endswith(".zip"):
                if self.ref != self.data.default_branch:
                    return True
        if self.ref == self.data.default_branch:
            return False
        if self.data.category not in ["plugin", "theme"]:
            return False
        if not self.data.releases:
            return False
        return True

    async def validate_repository(self) -> None:
        """Validate."""

    @concurrent(concurrenttasks=10, backoff_time=5)
    async def update_repository(self, ignore_issues=False, force=False) -> None:
        """Update the repository"""

    async def common_validate(self, ignore_issues: bool = False) -> None:
        """Common validation steps of the repository."""
        self.validate.errors.clear()

        # Make sure the repository exist.
        self.logger.debug("%s Checking repository.", self)
        await self.common_update_data(ignore_issues=ignore_issues)

        # Get the content of hacs.json
        if RepositoryFile.HACS_JSON in [x.filename for x in self.tree]:
            if manifest := await self.async_get_hacs_json():
                self.repository_manifest = HacsManifest.from_dict(manifest)
                self.data.update_data(self.repository_manifest.to_dict())

    async def common_registration(self) -> None:
        """Common registration steps of the repository."""
        # Attach repository
        if self.repository_object is None:
            try:
                self.repository_object, etag = await self.async_get_legacy_repository_object(
                    etag=None if self.data.installed else self.data.etag_repository,
                )
                self.data.update_data(self.repository_object.attributes)
                self.data.etag_repository = etag
            except HacsNotModifiedException:
                self.logger.debug(
                    "Did not update %s, content was not modified", self.data.full_name
                )
                return

        # Set topics
        self.data.topics = self.data.topics

        # Set stargazers_count
        self.data.stargazers_count = self.data.stargazers_count

        # Set description
        self.data.description = self.data.description

    @concurrent(concurrenttasks=10, backoff_time=5)
    async def common_update(self, ignore_issues=False, force=False) -> bool:
        """Common information update steps of the repository."""
        self.logger.debug("%s Getting repository information", self)

        # Attach repository
        current_etag = self.data.etag_repository
        try:
            await self.common_update_data(ignore_issues=ignore_issues, force=force)
        except HacsRepositoryExistException:
            self.data.full_name = self.hacs.common.renamed_repositories[self.data.full_name]
            await self.common_update_data(ignore_issues=ignore_issues, force=force)

        except HacsException:
            if not ignore_issues and not force:
                return False

        if not self.data.installed and (current_etag == self.data.etag_repository) and not force:
            self.logger.debug("Did not update %s, content was not modified", self.data.full_name)
            return False

        # Update last updated
        if self.repository_object:
            self.data.last_updated = self.repository_object.attributes.get("pushed_at", 0)

            # Update last available commit
            await self.repository_object.set_last_commit()
            self.data.last_commit = self.repository_object.last_commit

        # Get the content of hacs.json
        if RepositoryFile.HACS_JSON in [x.filename for x in self.tree]:
            if manifest := await self.async_get_hacs_json():
                self.repository_manifest = HacsManifest.from_dict(manifest)
                self.data.update_data(self.repository_manifest.to_dict())

        # Update "info.md"
        self.additional_info = await self.async_get_info_file_contents()

        # Set last fetch attribute
        self.data.last_fetched = datetime.now()

        return True

    async def download_zip_files(self, validate) -> None:
        """Download ZIP archive from repository release."""
        try:
            contents = None
            target_ref = self.ref.split("/")[1]

            for release in self.releases.objects:
                self.logger.debug("%s ref: %s --- tag: %s", self, target_ref, release.tag_name)
                if release.tag_name == target_ref:
                    contents = release.assets
                    break

            if not contents:
                validate.errors.append(f"No assets found for release '{self.ref}'")
                return

            download_queue = QueueManager(hass=self.hacs.hass)

            for content in contents or []:
                download_queue.add(self.async_download_zip_file(content, validate))

            await download_queue.execute()
        except BaseException:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            validate.errors.append("Download was not completed")

    async def async_download_zip_file(self, content, validate) -> None:
        """Download ZIP archive from repository release."""
        try:
            filecontent = await self.hacs.async_download_file(content.download_url)

            if filecontent is None:
                validate.errors.append(f"[{content.name}] was not downloaded")
                return

            temp_dir = await self.hacs.hass.async_add_executor_job(tempfile.mkdtemp)
            temp_file = f"{temp_dir}/{self.data.filename}"

            result = await self.hacs.async_save_file(temp_file, filecontent)
            with zipfile.ZipFile(temp_file, "r") as zip_file:
                zip_file.extractall(self.content.path.local)

            def cleanup_temp_dir():
                """Cleanup temp_dir."""
                if os.path.exists(temp_dir):
                    self.logger.debug("Cleaning up %s", temp_dir)
                    shutil.rmtree(temp_dir)

            if result:
                self.logger.info("%s Download of %s completed", self, content.name)
                await self.hacs.hass.async_add_executor_job(cleanup_temp_dir)
                return

            validate.errors.append(f"[{content.name}] was not downloaded")
        except BaseException:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            validate.errors.append("Download was not completed")

    async def download_content(self) -> None:
        """Download the content of a directory."""
        contents = self.gather_files_to_download()
        if self.data.filename:
            self.logger.debug(self.data.filename)
        if not contents:
            raise HacsException("No content to download")

        download_queue = QueueManager(hass=self.hacs.hass)

        for content in contents:
            if self.data.content_in_root and self.data.filename:
                if content.name != self.data.filename:
                    continue
            download_queue.add(self.dowload_repository_content(content))
        await download_queue.execute()

    async def async_get_hacs_json(self, ref: str = None) -> dict[str, Any] | None:
        """Get the content of the hacs.json file."""
        try:
            response = await self.hacs.async_github_api_method(
                method=self.hacs.githubapi.repos.contents.get,
                raise_exception=False,
                repository=self.data.full_name,
                path=RepositoryFile.HACS_JSON,
                **{"params": {"ref": ref or version_to_download(self)}},
            )
            if response:
                return json.loads(decode_content(response.data.content))
        except BaseException:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            pass

    async def async_get_info_file_contents(self) -> str:
        """Get the content of the info.md file."""

        def _info_file_variants() -> tuple[str, ...]:
            name: str = "readme" if self.data.render_readme else "info"
            return (
                f"{name.upper()}.md",
                f"{name}.md",
                f"{name}.MD",
                f"{name.upper()}.MD",
                name.upper(),
                name,
            )

        info_files = [filename for filename in _info_file_variants() if filename in self.treefiles]

        if not info_files:
            return ""

        try:
            response = await self.hacs.async_github_api_method(
                method=self.hacs.githubapi.repos.contents.get,
                raise_exception=False,
                repository=self.data.full_name,
                path=info_files[0],
            )
            if response:
                return render_template(
                    decode_content(response.data.content)
                    .replace("<svg", "<disabled")
                    .replace("</svg", "</disabled"),
                    self,
                )
        except BaseException as exc:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            self.logger.error(exc)

        return ""

    def remove(self) -> None:
        """Run remove tasks."""
        self.logger.info("%s Starting removal", self)

        if self.hacs.repositories.is_registered(repository_id=str(self.data.id)):
            self.hacs.repositories.unregister(self)

    async def uninstall(self) -> None:
        """Run uninstall tasks."""
        self.logger.info("%s Removing", self)
        if not await self.remove_local_directory():
            raise HacsException("Could not uninstall")
        self.data.installed = False
        if self.data.category == "integration":
            if self.data.config_flow:
                await self.reload_custom_components()
            else:
                self.pending_restart = True
        elif self.data.category == "theme":
            try:
                await self.hacs.hass.services.async_call("frontend", "reload_themes", {})
            except BaseException:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
                pass

        await async_remove_store(self.hacs.hass, f"hacs/{self.data.id}.hacs")

        self.data.installed_version = None
        self.data.installed_commit = None
        self.hacs.hass.bus.async_fire(
            "hacs/repository",
            {"id": 1337, "action": "uninstall", "repository": self.data.full_name},
        )

    async def remove_local_directory(self) -> None:
        """Check the local directory."""

        try:
            if self.data.category == "python_script":
                local_path = f"{self.content.path.local}/{self.data.name}.py"
            elif self.data.category == "theme":
                path = (
                    f"{self.hacs.core.config_path}/"
                    f"{self.hacs.configuration.theme_path}/"
                    f"{self.data.name}.yaml"
                )
                if os.path.exists(path):
                    os.remove(path)
                local_path = self.content.path.local
            elif self.data.category == "integration":
                if not self.data.domain:
                    if domain := DOMAIN_OVERRIDES.get(self.data.full_name):
                        self.data.domain = domain
                        self.content.path.local = self.localpath
                    else:
                        self.logger.error("%s Missing domain", self)
                        return False
                local_path = self.content.path.local
            else:
                local_path = self.content.path.local

            if os.path.exists(local_path):
                if not is_safe(self.hacs, local_path):
                    self.logger.error("%s Path %s is blocked from removal", self, local_path)
                    return False
                self.logger.debug("%s Removing %s", self, local_path)

                if self.data.category in ["python_script"]:
                    os.remove(local_path)
                else:
                    shutil.rmtree(local_path)

                while os.path.exists(local_path):
                    await sleep(1)
            else:
                self.logger.debug(
                    "%s Presumed local content path %s does not exist", self, local_path
                )

        except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            self.logger.debug("%s Removing %s failed with %s", self, local_path, exception)
            return False
        return True

    async def async_pre_registration(self) -> None:
        """Run pre registration steps."""

    @concurrent(concurrenttasks=10, backoff_time=5)
    async def async_registration(self, ref=None) -> None:
        """Run registration steps."""
        await self.async_pre_registration()

        if ref is not None:
            self.data.selected_tag = ref
            self.ref = ref
            self.force_branch = True

        if not await self.validate_repository():
            return False

        # Run common registration steps.
        await self.common_registration()

        # Set correct local path
        self.content.path.local = self.localpath

        # Run local post registration steps.
        await self.async_post_registration()

    async def async_post_registration(self) -> None:
        """Run post registration steps."""
        await self.hacs.validation.async_run_repository_checks(self)

    async def async_pre_install(self) -> None:
        """Run pre install steps."""

    async def _async_pre_install(self) -> None:
        """Run pre install steps."""
        self.logger.info("Running pre installation steps")
        await self.async_pre_install()
        self.logger.info("Pre installation steps completed")

    async def async_install(self) -> None:
        """Run install steps."""
        await self._async_pre_install()
        self.logger.info("Running installation steps")
        await self.async_install_repository()
        self.logger.info("Installation steps completed")
        await self._async_post_install()

    async def async_post_installation(self) -> None:
        """Run post install steps."""

    async def _async_post_install(self) -> None:
        """Run post install steps."""
        self.logger.info("Running post installation steps")
        await self.async_post_installation()
        self.data.new = False
        self.hacs.hass.bus.async_fire(
            "hacs/repository",
            {"id": 1337, "action": "install", "repository": self.data.full_name},
        )
        self.logger.info("Post installation steps completed")

    async def async_install_repository(self) -> None:
        """Common installation steps of the repository."""
        persistent_directory = None
        await self.update_repository(force=True)
        if self.content.path.local is None:
            raise HacsException("repository.content.path.local is None")
        self.validate.errors.clear()

        if not self.can_download:
            raise HacsException("The version of Home Assistant is not compatible with this version")

        version = version_to_download(self)
        if version == self.data.default_branch:
            self.ref = version
        else:
            self.ref = f"tags/{version}"

        if self.data.installed and self.data.category == "netdaemon":
            persistent_directory = BackupNetDaemon(hacs=self.hacs, repository=self)
            await self.hacs.hass.async_add_executor_job(persistent_directory.create)

        elif self.data.persistent_directory:
            if os.path.exists(f"{self.content.path.local}/{self.data.persistent_directory}"):
                persistent_directory = Backup(
                    hacs=self.hacs,
                    local_path=f"{self.content.path.local}/{self.data.persistent_directory}",
                    backup_path=tempfile.gettempdir() + "/hacs_persistent_directory/",
                )
                await self.hacs.hass.async_add_executor_job(persistent_directory.create)

        if self.data.installed and not self.content.single:
            backup = Backup(hacs=self.hacs, local_path=self.content.path.local)
            await self.hacs.hass.async_add_executor_job(backup.create)

        self.hacs.log.debug("%s Local path is set to %s", self, self.content.path.local)
        self.hacs.log.debug("%s Remote path is set to %s", self, self.content.path.remote)

        if self.data.zip_release and version != self.data.default_branch:
            await self.download_zip_files(self.validate)
        else:
            await self.download_content()

        if self.validate.errors:
            for error in self.validate.errors:
                self.logger.error(error)
            if self.data.installed and not self.content.single:
                await self.hacs.hass.async_add_executor_job(backup.restore)

        if self.data.installed and not self.content.single:
            await self.hacs.hass.async_add_executor_job(backup.cleanup)

        if persistent_directory is not None:
            await self.hacs.hass.async_add_executor_job(persistent_directory.restore)
            await self.hacs.hass.async_add_executor_job(persistent_directory.cleanup)

        if self.validate.success:
            self.data.installed = True
            self.data.installed_commit = self.data.last_commit

            if version == self.data.default_branch:
                self.data.installed_version = None
            else:
                self.data.installed_version = version

    async def async_get_legacy_repository_object(
        self,
        etag: str | None = None,
    ) -> tuple[AIOGitHubAPIRepository, Any | None]:
        """Return a repository object."""
        try:
            github = GitHub(
                self.hacs.configuration.token,
                self.hacs.session,
                headers={
                    "User-Agent": f"HACS/{self.hacs.version}",
                    "Accept": ACCEPT_HEADERS["preview"],
                },
            )
            repository = await github.get_repo(self.data.full_name, etag)
            return repository, github.client.last_response.etag
        except AIOGitHubAPINotModifiedException as exception:
            raise HacsNotModifiedException(exception) from exception
        except (ValueError, AIOGitHubAPIException, Exception) as exception:
            raise HacsException(exception) from exception

    def update_filenames(self) -> None:
        """Get the filename to target."""

    async def get_tree(self, ref: str):
        """Return the repository tree."""
        if self.repository_object is None:
            raise HacsException("No repository_object")
        try:
            tree = await self.repository_object.get_tree(ref)
            return tree
        except (ValueError, AIOGitHubAPIException) as exception:
            raise HacsException(exception) from exception

    async def get_releases(self, prerelease=False, returnlimit=5):
        """Return the repository releases."""
        if self.repository_object is None:
            raise HacsException("No repository_object")
        try:
            releases = await self.repository_object.get_releases(prerelease, returnlimit)
            return releases
        except (ValueError, AIOGitHubAPIException) as exception:
            raise HacsException(exception) from exception

    async def common_update_data(self, ignore_issues: bool = False, force: bool = False) -> None:
        """Common update data."""
        releases = []
        try:
            repository_object, etag = await self.async_get_legacy_repository_object(
                etag=None if force or self.data.installed else self.data.etag_repository,
            )
            self.repository_object = repository_object
            if self.data.full_name.lower() != repository_object.full_name.lower():
                self.hacs.common.renamed_repositories[
                    self.data.full_name
                ] = repository_object.full_name
                raise HacsRepositoryExistException
            self.data.update_data(repository_object.attributes)
            self.data.etag_repository = etag
        except HacsNotModifiedException:
            return
        except HacsRepositoryExistException:
            raise HacsRepositoryExistException from None
        except (AIOGitHubAPIException, HacsException) as exception:
            if not self.hacs.status.startup:
                self.logger.error("%s %s", self, exception)
            if not ignore_issues:
                self.validate.errors.append("Repository does not exist.")
                raise HacsException(exception) from exception

        # Make sure the repository is not archived.
        if self.data.archived and not ignore_issues:
            self.validate.errors.append("Repository is archived.")
            if self.data.full_name not in self.hacs.common.archived_repositories:
                self.hacs.common.archived_repositories.append(self.data.full_name)
            raise HacsRepositoryArchivedException(f"{self} Repository is archived.")

        # Make sure the repository is not in the blacklist.
        if self.hacs.repositories.is_removed(self.data.full_name) and not ignore_issues:
            self.validate.errors.append("Repository has been requested to be removed.")
            raise HacsException(f"{self} Repository has been requested to be removed.")

        # Get releases.
        try:
            releases = await self.get_releases(
                prerelease=self.data.show_beta,
                returnlimit=self.hacs.configuration.release_limit,
            )
            if releases:
                self.data.releases = True
                self.releases.objects = [x for x in releases if not x.draft]
                self.data.published_tags = [x.tag_name for x in self.releases.objects]
                self.data.last_version = next(iter(self.data.published_tags))

        except (AIOGitHubAPIException, HacsException):
            self.data.releases = False

        if not self.force_branch:
            self.ref = version_to_download(self)
        if self.data.releases:
            for release in self.releases.objects or []:
                if release.tag_name == self.ref:
                    assets = release.assets
                    if assets:
                        downloads = next(iter(assets)).attributes.get("download_count")
                        self.data.downloads = downloads

        self.hacs.log.debug("%s Running checks against %s", self, self.ref.replace("tags/", ""))

        try:
            self.tree = await self.get_tree(self.ref)
            if not self.tree:
                raise HacsException("No files in tree")
            self.treefiles = []
            for treefile in self.tree:
                self.treefiles.append(treefile.full_path)
        except (AIOGitHubAPIException, HacsException) as exception:
            if not self.hacs.status.startup and not ignore_issues:
                self.logger.error("%s %s", self, exception)
            if not ignore_issues:
                raise HacsException(exception) from None

    def gather_files_to_download(self) -> list[FileInformation]:
        """Return a list of file objects to be downloaded."""
        files = []
        tree = self.tree
        ref = f"{self.ref}".replace("tags/", "")
        releaseobjects = self.releases.objects
        category = self.data.category
        remotelocation = self.content.path.remote

        if self.should_try_releases:
            for release in releaseobjects or []:
                if ref == release.tag_name:
                    for asset in release.assets or []:
                        files.append(asset)
            if files:
                return files

        if self.content.single:
            for treefile in tree:
                if treefile.filename == self.data.file_name:
                    files.append(
                        FileInformation(
                            treefile.download_url, treefile.full_path, treefile.filename
                        )
                    )
            return files

        if category == "plugin":
            for treefile in tree:
                if treefile.path in ["", "dist"]:
                    if remotelocation == "dist" and not treefile.filename.startswith("dist"):
                        continue
                    if not remotelocation:
                        if not treefile.filename.endswith(".js"):
                            continue
                        if treefile.path != "":
                            continue
                    if not treefile.is_directory:
                        files.append(
                            FileInformation(
                                treefile.download_url, treefile.full_path, treefile.filename
                            )
                        )
            if files:
                return files

        if self.data.content_in_root:
            if not self.data.filename:
                if category == "theme":
                    tree = filter_content_return_one_of_type(self.tree, "", "yaml", "full_path")

        for path in tree:
            if path.is_directory:
                continue
            if path.full_path.startswith(self.content.path.remote):
                files.append(FileInformation(path.download_url, path.full_path, path.filename))
        return files

    @concurrent(concurrenttasks=10)
    async def dowload_repository_content(self, content: FileInformation) -> None:
        """Download content."""
        try:
            self.logger.debug("Downloading %s", content.name)

            filecontent = await self.hacs.async_download_file(content.download_url)

            if filecontent is None:
                self.validate.errors.append(f"[{content.name}] was not downloaded.")
                return

            # Save the content of the file.
            if self.content.single or content.path is None:
                local_directory = self.content.path.local

            else:
                _content_path = content.path
                if not self.data.content_in_root:
                    _content_path = _content_path.replace(f"{self.content.path.remote}", "")

                local_directory = f"{self.content.path.local}/{_content_path}"
                local_directory = local_directory.split("/")
                del local_directory[-1]
                local_directory = "/".join(local_directory)

            # Check local directory
            pathlib.Path(local_directory).mkdir(parents=True, exist_ok=True)

            local_file_path = (f"{local_directory}/{content.name}").replace("//", "/")

            result = await self.hacs.async_save_file(local_file_path, filecontent)
            if result:
                self.logger.info("Download of %s completed", content.name)
                return
            self.validate.errors.append(f"[{content.name}] was not downloaded.")

        except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            self.validate.errors.append(f"Download was not completed [{exception}]")
