"""Repository data."""
from datetime import datetime
from typing import List
import attr


@attr.s(auto_attribs=True)
class RepositoryData:
    """RepositoryData class."""

    id: int = 0
    full_name: str = None
    pushed_at: str = None
    archived: str = None
    description: str = None
    topics: List[str] = []
    fork: bool = False
    default_branch: str = None
    stargazers_count: int = 0
    last_commit: str = None

    def to_json(self):
        """Export to json."""
        return self.__dict__

    @staticmethod
    def from_dict(source: dict):
        """Set attributes from dicts."""
        data = RepositoryData()
        for key in source:
            if key in data.__dict__:
                if key == "pushed_at":
                    setattr(
                        data, key, datetime.strptime(source[key], "%Y-%m-%dT%H:%M:%SZ")
                    )
                else:
                    setattr(data, key, source[key])
        return data
