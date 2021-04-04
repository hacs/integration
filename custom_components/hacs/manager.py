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

    async def async_register_repository(
        self, category: HacsCategory, repository: str
    ) -> HacsRepository:
        """Register a HacsRepository."""
        repo = HacsRepository(self.hacs, category, repository)
        try:
            await repo.async_reload_repository()
        except SystemError:
            return None
        self._repositories["id"][str(repo.information.databaseId)] = repo
        self._repositories["name"][str(repo.identifier)] = repo
        return repo
