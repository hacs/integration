"""Base class for repositories."""
from __future__ import annotations
from dataclasses import dataclass
import base64
import json
from typing import Any

from awesomeversion import AwesomeVersion
from aiogithubapi import GitHubNotModifiedException

from ..enums import HacsCategory
from ..mixin import HacsMixin, LogMixin


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
        cls.homeassistant = (
            AwesomeVersion(cls.homeassistant) if cls.homeassistant else None
        )
        return cls


@dataclass
class HacsRepository(HacsMixin, LogMixin):
    """Base class for repositories."""

    full_name: str
    category: HacsCategory

    id: int | None = None  # pylint: disable=invalid-name
    description: str | None = None
    default_branch: str | None = None
    archived: bool | None = None
    stargazers_count: int | None = None
    topics: list[str] | None = None

    hacs_manifest: HacsManifest | None = None

    etag_repository: str | None = None
    etag_hacs_manifest: str | None = None

    @property
    def uses_releases(self) -> bool:
        """Boolean to indicate that the repository uses releases."""
        return False

    async def async_github_update_information(self) -> None:
        """Update repository information from github."""
        try:
            response = await self.hacs.githubapi.repos.get(
                self.full_name, **{"etag": self.etag_repository}
            )
            self.etag_repository = response.etag
        except GitHubNotModifiedException:
            return None

        if self.full_name != response.data.full_name:
            self.hacs.common.renamed_repositories.setdefault(
                self.full_name, response.data.full_name
            )

        ## Update hacs._repositories*
        self.id = str(response.data.id)
        self.description = response.data.description
        self.default_branch = response.data.default_branch
        self.archived = response.data.archived
        self.stargazers_count = response.data.stargazers_count
        self.topics = response.data.topics

        if hacs_manifest := await self.async_github_get_hacs_manifest():
            self.hacs_manifest = hacs_manifest

    async def async_github_get_hacs_manifest(
        self,
        ref: str | None = None,
    ) -> HacsManifest:
        """Get the HACS manifest from GitHub."""
        try:
            response = await self.hacs.githubapi.repos.contents.get(
                self.full_name,
                "hacs.json",
                **{
                    "query": {"ref": ref} if ref else {},
                    "etag": self.etag_hacs_manifest,
                },
            )
            self.etag_hacs_manifest = response.etag
        except GitHubNotModifiedException:
            return None

        return HacsManifest.from_dict(
            json.loads(
                base64.b64decode(bytearray(response.data.content, "utf-8")).decode()
            )
        )
