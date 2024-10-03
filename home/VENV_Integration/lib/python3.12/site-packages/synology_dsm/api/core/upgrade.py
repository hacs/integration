"""DSM Upgrade data and actions."""

from __future__ import annotations

from typing import TypedDict

from synology_dsm.api import SynoBaseApi


class UpgradeDataType(TypedDict, total=False):
    """Data type."""

    available: bool
    version: str
    version_details: dict
    reboot: str
    restart: str


class SynoCoreUpgrade(SynoBaseApi[UpgradeDataType]):
    """Class containing upgrade data and actions."""

    API_KEY = "SYNO.Core.Upgrade"
    API_SERVER_KEY = API_KEY + ".Server"

    async def update(self) -> None:
        """Updates Upgrade data."""
        raw_data = await self._dsm.get(self.API_SERVER_KEY, "check")
        if isinstance(raw_data, dict) and (data := raw_data.get("data")) is not None:
            self._data = data.get("update", data)

    @property
    def update_available(self) -> bool:
        """Gets available update info."""
        return self._data["available"]

    @property
    def available_version(self) -> str | None:
        """Gets available verion info."""
        return self._data.get("version")

    @property
    def available_version_details(self) -> dict | None:
        """Gets details about available verion."""
        return self._data.get("version_details")

    @property
    def reboot_needed(self) -> str | None:
        """Gets info if reboot is needed."""
        return self._data.get("reboot")

    @property
    def service_restarts(self) -> str | None:
        """Gets info if services are restarted."""
        return self._data.get("restart")
