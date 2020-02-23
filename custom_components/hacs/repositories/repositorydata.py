"""Repository data."""
from datetime import datetime
from typing import List
import attr


@attr.s(auto_attribs=True)
class RepositoryData:
    """RepositoryData class."""

    id: int = 0
    full_name: str = ""
    pushed_at: str = ""
    category: str = ""
    archived: bool = False
    description: str = ""
    manifest_name: str = None
    topics: List[str] = []
    fork: bool = False
    domain: str = ""
    default_branch: str = None
    stargazers_count: int = 0
    last_commit: str = ""
    file_name: str = ""
    content_in_root: bool = False
    zip_release: bool = False
    filename: str = ""
    render_readme: bool = False
    hide_default_branch: bool = False
    domains: List[str] = []
    country: List[str] = []
    authors: List[str] = []
    homeassistant: str = None  # Minimum Home Assistant version
    hacs: str = None  # Minimum HACS version
    persistent_directory: str = None
    iot_class: str = None

    @property
    def name(self):
        """Return the name."""
        if self.category == "integration":
            return self.domain
        return self.full_name.split("/")[-1]

    def to_json(self):
        """Export to json."""
        return self.__dict__

    @staticmethod
    def create_from_dict(source: dict):
        """Set attributes from dicts."""
        data = RepositoryData()
        for key in source:
            if key in data.__dict__:
                if key == "pushed_at":
                    setattr(
                        data, key, datetime.strptime(source[key], "%Y-%m-%dT%H:%M:%SZ")
                    )
                elif key == "county":
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
            if key in self.__dict__:
                if key == "pushed_at":
                    setattr(
                        self, key, datetime.strptime(data[key], "%Y-%m-%dT%H:%M:%SZ")
                    )
                elif key == "county":
                    if isinstance(data[key], str):
                        setattr(self, key, [data[key]])
                    else:
                        setattr(self, key, data[key])
                else:
                    setattr(self, key, data[key])
