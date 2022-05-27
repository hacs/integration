"""Data handler for HACS."""
import asyncio
from datetime import datetime

from homeassistant.core import callback
from homeassistant.util import json as json_util

from ..base import HacsBase
from ..enums import HacsDispatchEvent, HacsGitHubRepo
from ..repositories.base import TOPIC_FILTER, HacsManifest, HacsRepository
from .logger import get_hacs_logger
from .path import is_safe
from .store import async_load_from_store, async_save_to_store

DEFAULT_BASE_REPOSITORY_DATA = (
    ("authors", []),
    ("category", ""),
    ("description", ""),
    ("domain", None),
    ("downloads", 0),
    ("etag_repository", None),
    ("full_name", ""),
    ("last_updated", 0),
    ("hide", False),
    ("new", False),
    ("stargazers_count", 0),
    ("topics", []),
)

DEFAULT_EXTENDED_REPOSITORY_DATA = (
    ("archived", False),
    ("config_flow", False),
    ("default_branch", None),
    ("description", ""),
    ("first_install", False),
    ("installed_commit", None),
    ("installed", False),
    ("last_commit", None),
    ("last_version", None),
    ("manifest_name", None),
    ("open_issues", 0),
    ("published_tags", []),
    ("pushed_at", ""),
    ("releases", False),
    ("selected_tag", None),
    ("show_beta", False),
    ("stargazers_count", 0),
    ("topics", []),
)


class HacsData:
    """HacsData class."""

    def __init__(self, hacs: HacsBase):
        """Initialize."""
        self.logger = get_hacs_logger()
        self.hacs = hacs
        self.content = {}

    async def async_force_write(self, _=None):
        """Force write."""
        await self.async_write(force=True)

    async def async_write(self, force: bool = False) -> None:
        """Write content to the store files."""
        if not force and self.hacs.system.disabled:
            return

        self.logger.debug("<HacsData async_write> Saving data")

        # Hacs
        await async_save_to_store(
            self.hacs.hass,
            "hacs",
            {
                "archived_repositories": self.hacs.common.archived_repositories,
                "renamed_repositories": self.hacs.common.renamed_repositories,
                "ignored_repositories": self.hacs.common.ignored_repositories,
            },
        )
        await self._async_store_content_and_repos()

    async def _async_store_content_and_repos(self, _=None):  # bb: ignore
        """Store the main repos file and each repo that is out of date."""
        # Repositories
        self.content = {}
        for repository in self.hacs.repositories.list_all:
            if repository.data.category in self.hacs.common.categories:
                self.async_store_repository_data(repository)

        await async_save_to_store(self.hacs.hass, "repositories", self.content)
        for event in (HacsDispatchEvent.REPOSITORY, HacsDispatchEvent.CONFIG):
            self.hacs.async_dispatch(event, {})

    @callback
    def async_store_repository_data(self, repository: HacsRepository) -> dict:
        """Store the repository data."""
        data = {"repository_manifest": repository.repository_manifest.manifest}

        for key, default_value in DEFAULT_BASE_REPOSITORY_DATA:
            if (value := repository.data.__getattribute__(key)) != default_value:
                data[key] = value

        if repository.data.installed:
            for key, default_value in DEFAULT_EXTENDED_REPOSITORY_DATA:
                if (value := repository.data.__getattribute__(key)) != default_value:
                    data[key] = value
            data["version_installed"] = repository.data.installed_version

        if repository.data.last_fetched:
            data["last_fetched"] = repository.data.last_fetched.timestamp()

        self.content[str(repository.data.id)] = data

    async def restore(self):
        """Restore saved data."""
        self.hacs.status.new = False
        hacs = await async_load_from_store(self.hacs.hass, "hacs") or {}
        repositories = await async_load_from_store(self.hacs.hass, "repositories") or {}

        if not hacs and not repositories:
            # Assume new install
            self.hacs.status.new = True
            self.logger.info("<HacsData restore> Loading base repository information")
            repositories = await self.hacs.hass.async_add_executor_job(
                json_util.load_json,
                f"{self.hacs.core.config_path}/custom_components/hacs/utils/default.repositories",
            )

        self.logger.info("<HacsData restore> Restore started")

        # Hacs
        self.hacs.common.archived_repositories = []
        self.hacs.common.ignored_repositories = []
        self.hacs.common.renamed_repositories = {}

        # Clear out doubble renamed values
        renamed = hacs.get("renamed_repositories", {})
        for entry in renamed:
            value = renamed.get(entry)
            if value not in renamed:
                self.hacs.common.renamed_repositories[entry] = value

        # Clear out doubble archived values
        for entry in hacs.get("archived_repositories", []):
            if entry not in self.hacs.common.archived_repositories:
                self.hacs.common.archived_repositories.append(entry)

        # Clear out doubble ignored values
        for entry in hacs.get("ignored_repositories", []):
            if entry not in self.hacs.common.ignored_repositories:
                self.hacs.common.ignored_repositories.append(entry)

        try:
            await self.register_unknown_repositories(repositories)

            for entry, repo_data in repositories.items():
                if entry == "0":
                    # Ignore repositories with ID 0
                    self.logger.debug(
                        "<HacsData restore> Found repository with ID %s - %s", entry, repo_data
                    )
                    continue
                self.async_restore_repository(entry, repo_data)

            self.logger.info("<HacsData restore> Restore done")
        except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
            self.logger.critical(
                "<HacsData restore> [%s] Restore Failed!", exception, exc_info=exception
            )
            return False
        return True

    async def register_unknown_repositories(self, repositories):
        """Registry any unknown repositories."""
        register_tasks = [
            self.hacs.async_register_repository(
                repository_full_name=repo_data["full_name"],
                category=repo_data["category"],
                check=False,
                repository_id=entry,
            )
            for entry, repo_data in repositories.items()
            if entry != "0" and not self.hacs.repositories.is_registered(repository_id=entry)
        ]
        if register_tasks:
            await asyncio.gather(*register_tasks)

    @callback
    def async_restore_repository(self, entry, repository_data):
        """Restore repository."""
        full_name = repository_data["full_name"]
        if not (repository := self.hacs.repositories.get_by_full_name(full_name)):
            self.logger.error("<HacsData restore> Did not find %s (%s)", full_name, entry)
            return
        # Restore repository attributes
        self.hacs.repositories.set_repository_id(repository, entry)
        repository.data.authors = repository_data.get("authors", [])
        repository.data.description = repository_data.get("description", "")
        repository.data.downloads = repository_data.get("downloads", 0)
        repository.data.last_updated = repository_data.get("last_updated", 0)
        repository.data.etag_repository = repository_data.get("etag_repository")
        repository.data.topics = [
            topic for topic in repository_data.get("topics", []) if topic not in TOPIC_FILTER
        ]
        repository.data.domain = repository_data.get("domain")
        repository.data.stargazers_count = repository_data.get(
            "stargazers_count"
        ) or repository_data.get("stars", 0)
        repository.releases.last_release = repository_data.get("last_release_tag")
        repository.data.releases = repository_data.get("releases", False)
        repository.data.hide = repository_data.get("hide", False)
        repository.data.installed = repository_data.get("installed", False)
        repository.data.new = repository_data.get("new", False)
        repository.data.selected_tag = repository_data.get("selected_tag")
        repository.data.show_beta = repository_data.get("show_beta", False)
        repository.data.last_version = repository_data.get("last_version")
        repository.data.last_commit = repository_data.get("last_commit")
        repository.data.installed_version = repository_data.get("version_installed")
        repository.data.installed_commit = repository_data.get("installed_commit")
        repository.data.manifest_name = repository_data.get("manifest_name")

        if last_fetched := repository_data.get("last_fetched"):
            repository.data.last_fetched = datetime.fromtimestamp(last_fetched)

        repository.repository_manifest = HacsManifest.from_dict(
            repository_data.get("repository_manifest", {})
        )

        if repository.localpath is not None and is_safe(self.hacs, repository.localpath):
            # Set local path
            repository.content.path.local = repository.localpath

        if repository.data.installed:
            repository.data.first_install = False

        if full_name == HacsGitHubRepo.INTEGRATION:
            repository.data.installed_version = self.hacs.version
            repository.data.installed = True
