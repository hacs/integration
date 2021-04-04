"""HACS repository."""
from dataclasses import dataclass
from typing import List
from aiogithubapi.objects.repository.content import (
    AIOGitHubAPIRepositoryTreeContent,
)

from .base import HacsBase
from .dataclass import RepositoryIdentifier
from .enums import HacsCategory
from .gql.repository_base import RepositoryBaseInformation, repository_base


@dataclass
class RepositoryOptions:
    """Dataclass for repository options."""

    pre_releases = False


class HacsRepository:
    """HACS repository."""

    def __init__(self, hacs: HacsBase, category: HacsCategory, repository: str):

        self.hacs: HacsBase = hacs
        self.identifier = RepositoryIdentifier(repository)
        self.category: HacsCategory = HacsCategory(category)
        self.options = RepositoryOptions()
        self.information: RepositoryBaseInformation = RepositoryBaseInformation({})
        self.tree: List[AIOGitHubAPIRepositoryTreeContent] = []

    @property
    def representation(self) -> str:
        """Return a string representation of the repository."""
        return f"<{self.category} {self.identifier}>"

    async def async_reload_repository(self):
        """Reload information about the repository from gitHub."""
        self.information = await repository_base(
            self.hacs.github, self.identifier, self.options.pre_releases
        )

        response = await self.hacs.github.client.get(
            endpoint=f"/repos/{self.identifier}/git/trees/{self.information.defaultBranchRef}",
            params={"recursive": "1"},
        )
        self.tree = [
            AIOGitHubAPIRepositoryTreeContent(
                x, self.identifier, self.information.defaultBranchRef
            )
            for x in response.data.get("tree", [])
        ]
