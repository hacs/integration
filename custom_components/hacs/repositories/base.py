"""Base class for repositories."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta, datetime
import json
from typing import Any

from aiogithubapi import GitHubNotModifiedException
from awesomeversion import AwesomeVersion

from ..exceptions import HacsException

from ..enums import HacsCategory, RepositoryFile
from ..mixin import HacsMixin, LogMixin
from ..utils.decode import decode_content


@dataclass
class HacsManifest:
    """Representation of ta hacs.json file."""

    name: str | None = None
    content_in_root: bool = False
    zip_release: bool = False
    filename: str | None = None
    render_readme: bool = False
    country: list[str] | None = None
    hacs: AwesomeVersion | None = None
    homeassistant: AwesomeVersion | None = None
    persistent_directory: str | None = None
    hide_default_branch: bool = False

    @staticmethod
    def from_dict(data: dict[str, Any]) -> HacsManifest:
        """Initialize from dict."""
        cls = HacsManifest()
        for key in data:
            if hasattr(cls, key):
                setattr(cls, key, data[key])

        if cls.country is not None:
            if isinstance(cls.country, str):
                cls.country = [cls.country]

        cls.hacs = AwesomeVersion(cls.hacs) if cls.hacs else None
        cls.homeassistant = AwesomeVersion(cls.homeassistant) if cls.homeassistant else None
        return cls


@dataclass
class Repository(HacsMixin, LogMixin):  # pylint: disable=too-many-instance-attributes
    """Base class for repositories."""

    full_name: str
    category: HacsCategory

    installed: bool = False

    id: str | None = None  # pylint: disable=invalid-name
    description: str | None = None
    default_branch: str | None = None
    archived: bool | None = None
    stargazers_count: int | None = None
    topics: list[str] | None = None
    updated_at: str | None = None

    repository_tree: tuple[str] | None = None
    hacs_manifest: HacsManifest | None = None

    etag_repository: str | None = None
    etag_repository_tree: str | None = None
    etag_hacs_manifest: str | None = None

    @property
    def uses_releases(self) -> bool:
        """Boolean to indicate that the repository uses releases."""
        return False

    @property
    def update_strategy(self) -> timedelta:
        """Return the update strategy."""
        if self.installed or self.updated_at is None:
            return timedelta(hours=2)

        updated = datetime.strptime(self.updated_at, "%Y-%m-%dT%H:%M:%SZ")
        now = datetime.now()

        if updated > (now - timedelta(days=30)):
            return timedelta(hours=25)

        return timedelta(days=7)

    def repository_tree_contains(self, path: str) -> bool:
        """Check if the tree contains a file."""
        if self.repository_tree is None:
            return False
        for tree in self.repository_tree:
            if tree.split("/")[-1] == path:
                return True
        return False

    async def async_github_update_information(self) -> None:
        """Update repository information from github."""
        try:
            response = await self.hacs.githubapi.repos.get(
                repository=self.full_name,
                **{"etag": self.etag_repository},
            )
            self.etag_repository = response.etag
        except GitHubNotModifiedException:
            return None
        except HacsException as exception:
            self.log.error(exception)
            return None

        if self.full_name != response.data.full_name:
            self.hacs.common.renamed_repositories.setdefault(
                self.full_name, response.data.full_name
            )

        self.id = str(response.data.id)
        self.description = response.data.description
        self.default_branch = response.data.default_branch
        self.archived = response.data.archived
        self.stargazers_count = response.data.stargazers_count
        self.topics = response.data.topics

        if repository_tree := await self.async_github_get_tree(tree_sha=self.default_branch):
            self.repository_tree = repository_tree

        if hacs_manifest := await self.async_github_get_file_contents(
            file_path=RepositoryFile.HACS_JSON
        ):
            self.hacs_manifest = HacsManifest.from_dict(json.loads(hacs_manifest))

    async def async_github_get_tree(
        self,
        tree_sha: str,
    ) -> tuple[str] | None:
        """Get the tree from GitHub."""
        try:
            response = await self.hacs.async_github_api_method(
                self.hacs.githubapi.repos.git.get_tree,
                repository=self.full_name,
                tree_sha=tree_sha,
                **{"etag": self.etag_repository_tree},
            )
            self.etag_repository_tree = response.etag
        except GitHubNotModifiedException:
            return None
        except HacsException:
            return None

        return tuple(tree.path for tree in response.data.tree or [])

    async def async_github_get_file_contents(
        self,
        file_path: str,
        ref: str | None = None,
    ) -> str | None:
        """Get the HACS manifest from GitHub."""
        if not self.repository_tree_contains(file_path):
            return

        try:
            response = await self.hacs.async_github_api_method(
                self.hacs.githubapi.repos.contents.get,
                repository=self.full_name,
                path=file_path,
                **{
                    "query": {"ref": ref} if ref else {},
                    "etag": self.etag_hacs_manifest,
                },
            )
            self.etag_hacs_manifest = response.etag
        except GitHubNotModifiedException:
            return None
        except HacsException:
            return None

        return decode_content(response.data.content)
