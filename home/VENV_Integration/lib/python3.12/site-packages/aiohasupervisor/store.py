"""Store client for supervisor."""

from .client import _SupervisorComponentClient
from .const import ResponseType
from .models.addons import (
    Repository,
    StoreAddon,
    StoreAddonComplete,
    StoreAddonsList,
    StoreAddonUpdate,
    StoreAddRepository,
    StoreInfo,
)


class StoreClient(_SupervisorComponentClient):
    """Handles store access in Supervisor."""

    async def info(self) -> StoreInfo:
        """Get store info."""
        result = await self._client.get("store")
        return StoreInfo.from_dict(result.data)

    async def addons_list(self) -> list[StoreAddon]:
        """Get list of store addons."""
        result = await self._client.get("store/addons")
        return StoreAddonsList.from_dict(result.data).addons

    async def addon_info(self, addon: str) -> StoreAddonComplete:
        """Get store addon info."""
        result = await self._client.get(f"store/addons/{addon}")
        return StoreAddonComplete.from_dict(result.data)

    async def addon_changelog(self, addon: str) -> str:
        """Get addon changelog."""
        result = await self._client.get(
            f"store/addons/{addon}/changelog", response_type=ResponseType.TEXT
        )
        return result.data

    async def addon_documentation(self, addon: str) -> str:
        """Get addon documentation."""
        result = await self._client.get(
            f"store/addons/{addon}/documentation", response_type=ResponseType.TEXT
        )
        return result.data

    async def install_addon(self, addon: str) -> None:
        """Install an addon."""
        await self._client.post(f"store/addons/{addon}/install")

    async def update_addon(
        self, addon: str, options: StoreAddonUpdate | None = None
    ) -> None:
        """Update an addon to latest version."""
        await self._client.post(
            f"store/addons/{addon}/update", json=options.to_dict() if options else None
        )

    async def reload(self) -> None:
        """Reload the store."""
        await self._client.post("store/reload")

    async def repositories_list(self) -> list[Repository]:
        """Get list of repositories."""
        result = await self._client.get("store/repositories")
        # This API is inconsistent with Supervisor's API model, data should be
        # a dictionary with a "repositories" field. It would break the CLI like
        # this but the CLI doesn't use it so it went unnoticed.
        return [Repository.from_dict(repo) for repo in result.data]

    async def repository_info(self, repository: str) -> Repository:
        """Get repository info."""
        result = await self._client.get(f"store/repositories/{repository}")
        return Repository.from_dict(result.data)

    async def add_repository(self, options: StoreAddRepository) -> None:
        """Add a repository to the store."""
        await self._client.post("store/repositories", json=options.to_dict())

    async def remove_repository(self, repository: str) -> None:
        """Remove a repository from the store."""
        await self._client.delete(f"store/repositories/{repository}")

    # Omitted for now - Icon/Logo endpoints
