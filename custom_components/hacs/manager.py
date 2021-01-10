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
        self._repositories: Dict[str, Dict[str, HacsRepository]] = {}

    def get_repository(
        self, name: str = None, database_id: str = None
    ) -> HacsRepository:
        """Get a HacsRepository."""
        if database_id is not None:
            return self._repositories["ids"].get(database_id)
        if name is not None:
            return self._repositories["ids"].get(name)
        return None

    async def register_repository(
        self, category: HacsCategory, repository: str
    ) -> HacsRepository:
        """Register a HacsRepository."""
        repo = HacsRepository(self.hacs, category, repository)
        await self.reload_repository(repo)
        self._repositories["ids"][repo.identifier] = repo
        self._repositories["names"][repo.information.databaseId] = repo
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
