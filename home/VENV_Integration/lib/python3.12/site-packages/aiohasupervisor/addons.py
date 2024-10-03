"""Addons client for Supervisor."""

from typing import Any

from .client import _SupervisorComponentClient
from .const import ResponseType
from .models.addons import (
    AddonsConfigValidate,
    AddonsList,
    AddonsOptions,
    AddonsSecurityOptions,
    AddonsStats,
    AddonsUninstall,
    InstalledAddon,
    InstalledAddonComplete,
)


class AddonsClient(_SupervisorComponentClient):
    """Handles installed addon access in Supervisor."""

    async def list(self) -> list[InstalledAddon]:
        """Get installed addons."""
        result = await self._client.get("addons")
        return AddonsList.from_dict(result.data).addons

    async def addon_info(self, addon: str) -> InstalledAddonComplete:
        """Get all info for addon."""
        result = await self._client.get(f"addons/{addon}/info")
        return InstalledAddonComplete.from_dict(result.data)

    async def uninstall_addon(
        self,
        addon: str,
        options: AddonsUninstall | None = None,
    ) -> None:
        """Uninstall an addon."""
        await self._client.post(
            f"addons/{addon}/uninstall",
            json=options.to_dict() if options else None,
        )

    async def start_addon(self, addon: str) -> None:
        """Start an addon."""
        await self._client.post(f"addons/{addon}/start")

    async def stop_addon(self, addon: str) -> None:
        """Stop an addon."""
        await self._client.post(f"addons/{addon}/stop")

    async def restart_addon(self, addon: str) -> None:
        """Restart an addon."""
        await self._client.post(f"addons/{addon}/restart")

    async def addon_options(self, addon: str, options: AddonsOptions) -> None:
        """Set options for addon."""
        await self._client.post(f"addons/{addon}/options", json=options.to_dict())

    async def addon_config_validate(
        self,
        addon: str,
        config: dict[str, Any],
    ) -> AddonsConfigValidate:
        """Validate config for an addon."""
        result = await self._client.post(
            f"addons/{addon}/options/validate",
            response_type=ResponseType.JSON,
            json=config,
        )
        return AddonsConfigValidate.from_dict(result.data)

    async def addon_config(self, addon: str) -> dict[str, Any]:
        """Get config for addon."""
        result = await self._client.get(f"addons/{addon}/options/config")
        return result.data

    async def rebuild_addon(self, addon: str) -> None:
        """Rebuild an addon (only available for local addons built from source)."""
        await self._client.post(f"addons/{addon}/rebuild")

    async def addon_stdin(self, addon: str, stdin: bytes) -> None:
        """Write to stdin of an addon (if supported by addon)."""
        await self._client.post(f"addons/{addon}/stdin", data=stdin)

    async def addon_security(self, addon: str, options: AddonsSecurityOptions) -> None:
        """Set security options for addon."""
        await self._client.post(f"addons/{addon}/security", json=options.to_dict())

    async def addon_stats(self, addon: str) -> AddonsStats:
        """Get stats for addon."""
        result = await self._client.get(f"addons/{addon}/stats")
        return AddonsStats.from_dict(result.data)

    # Omitted for now - Log endpoints
