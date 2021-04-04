"""HACS repository manager."""
from typing import Dict

from .enums import HacsCategory
from .base import HacsBase
from .repository import HacsRepository


class HacsRepositoryManager:
    """HACS repository manager."""

    def __init__(self, hacs: HacsBase) -> None:
        """Initialise the HacsRepositoryManager class."""
        self.hacs = hacs
        self._repositories: Dict[str, Dict[str, HacsRepository]] = {
            "id": {},
            "name": {},
        }

    def get_repository(
        self, name: str = None, database_id: str = None
    ) -> HacsRepository:
        """Get a HacsRepository."""
        if database_id is not None:
            return self._repositories["id"].get(database_id)
        if name is not None:
            return self._repositories["name"].get(name)
        return None

    async def register_repository(
        self, category: HacsCategory, repository: str
    ) -> HacsRepository:
        """Register a HacsRepository."""
        repo = HacsRepository(self.hacs, category, repository)
        await self.async_reload_repository(repo)
        self._repositories["id"][repo.identifier] = repo
        self._repositories["name"][repo.information.databaseId] = repo
        return repo

    async def async_reload_repository(self, repository: HacsRepository) -> None:
        """Reload information about the repository from gitHub."""
        await repository.async_reload_repository()
