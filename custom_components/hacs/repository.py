"""HACS repository."""
from typing import List
from aiogithubapi.objects.repository.content import (
    AIOGitHubAPIRepositoryTreeContent,
)

from .base import HacsBase
from .dataclass import RepositoryIdentifier
from .enums import HacsCategory
from .gql.repository_base import RepositoryBaseInformation


class HacsRepository:
    """HACS repository."""

    def __init__(self, hacs: HacsBase, category: HacsCategory, repository: str):

        self.hacs: HacsBase = hacs
        self.identifier = RepositoryIdentifier(repository)
        self.category: HacsCategory = HacsCategory(category)
        self.information: RepositoryBaseInformation = RepositoryBaseInformation({})
        self.tree: List[AIOGitHubAPIRepositoryTreeContent] = []

    @property
    def representation(self) -> str:
        """Return a string representation of the repository."""
        return f"<{self.category.title()} {self.identifier}>"
