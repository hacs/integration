"""HACS repository manager."""
from typing import Dict

from aiogithubapi.objects.repository.content import AIOGitHubAPIRepositoryTreeContent
from .enums import HacsCategory
from .base import HacsBase
from .repository import HacsRepository
from .gql.repository_base import repository_base


class HacsRepositoryManager:
    """HACS repository manager."""

    def __init__(self, hacs: HacsBase) -> None:
        """Initialise the HacsRepositoryManager class."""
        self.hacs = hacs
        self._repositories: Dict[str, HacsRepository] = {}

    async def get(self, category: HacsCategory, repository: str) -> HacsRepository:
        """Get a HacsRepository, if it's unknown it will be created."""
        if repository in self._repositories:
            return self._repositories[repository]
        return await self._add_repository(category, repository)

    async def _add_repository(
        self, category: HacsCategory, repository: str
    ) -> HacsRepository:
        """Private method to add a repository"""
        repo = HacsRepository(self.hacs, category, repository)
        self._repositories[repository] = repo
        return repo

    async def reload_repository(self, repository: HacsRepository) -> None:
        """Reload information about the repository from gitHub."""
        repository.information = await repository_base(
            self.hacs.github, repository.identifier
        )

        _raw_tree = await self.hacs.github.client.get(
            endpoint=(
                f"/repos/{repository.identifier}/git/trees/",
                repository.information.defaultBranchRef,
            ),
            params={"recursive": "1"},
        )
        repository.tree = [
            AIOGitHubAPIRepositoryTreeContent(
                x, repository.identifier, repository.information.defaultBranchRef
            )
            for x in _raw_tree.get("tree", [])
        ]
