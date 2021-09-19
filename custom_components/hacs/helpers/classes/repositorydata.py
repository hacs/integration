"""Repository data."""
from datetime import datetime
import json
from typing import List, Optional

import attr
from homeassistant.helpers.json import JSONEncoder

REPO_DATA_KEYS = {
    "archived",
    "authors",
    "category",
    "content_in_root",
    "country",
    "config_flow",
    "default_branch",
    "description",
    "domain",
    "domains",
    "downloads",
    "etag_repository",
    "file_name",
    "filename",
    "first_install",
    "fork",
    "full_name",
    "full_name_lower",
    "hacs",
    "hide",
    "hide_default_branch",
    "homeassistant",
    "id",
    "iot_class",
    "installed",
    "installed_commit",
    "installed_version",
    "open_issues",
    "last_version",
    "last_updated",
    "manifest_name",
    "new",
    "persistent_directory",
    "pushed_at",
    "releases",
    "render_readme",
    "published_tags",
    "selected_tag",
    "show_beta",
    "stargazers_count",
    "topics",
    "zip_release",
}


@attr.s(slots=True)
class RepositoryData:
    """RepositoryData class."""

    archived: bool = attr.ib(default=False)
    authors: List[str] = attr.ib(default=[])
    category: str = attr.ib(default="")
    content_in_root: bool = attr.ib(default=False)
    country: List[str] = attr.ib(default=[])
    config_flow: bool = attr.ib(default=False)
    default_branch: str = attr.ib(default=None)
    description: str = attr.ib(default="")
    domain: str = attr.ib(default="")
    domains: List[str] = attr.ib(default=[])
    downloads: int = attr.ib(default=0)
    etag_repository: str = attr.ib(default=None)
    file_name: str = attr.ib(default="")
    filename: str = attr.ib(default="")
    first_install: bool = attr.ib(default=False)
    fork: bool = attr.ib(default=False)
    full_name: str = attr.ib(default="")
    full_name_lower: str = attr.ib(default="")
    hacs: str = attr.ib(default=None)  # Minimum HACS version
    hide: bool = attr.ib(default=False)
    hide_default_branch: bool = attr.ib(default=False)
    homeassistant: str = attr.ib(default=None)  # Minimum Home Assistant version
    id: int = attr.ib(default=0)
    iot_class: str = attr.ib(default=None)
    installed: bool = attr.ib(default=False)
    installed_commit: str = attr.ib(default=None)
    installed_version: str = attr.ib(default=None)
    open_issues: int = attr.ib(default=0)
    last_commit: str = attr.ib(default=None)
    last_version: str = attr.ib(default=None)
    last_updated: str = attr.ib(default=0)
    manifest_name: str = attr.ib(default=None)
    new: bool = attr.ib(default=True)
    persistent_directory: str = attr.ib(default=None)
    pushed_at: str = attr.ib(default="")
    releases: bool = attr.ib(default=False)
    render_readme: bool = attr.ib(default=False)
    published_tags: List[str] = attr.ib(default=[])
    selected_tag: str = attr.ib(default=None)
    show_beta: bool = attr.ib(default=False)
    stargazers_count: int = attr.ib(default=0)
    topics: List[str] = attr.ib(default=[])
    zip_release: bool = attr.ib(default=False)
    _storage_data: Optional[dict] = attr.ib(default=None)

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
        return attr.asdict(self, filter=lambda attr, _: attr.name != "_storage_data")

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
            if key not in REPO_DATA_KEYS:
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
            if key not in REPO_DATA_KEYS:
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
