"""DSM Information data."""

from __future__ import annotations

from typing import TypedDict

from synology_dsm.api import SynoBaseApi


class DsmInformationDataType(TypedDict, total=False):
    """Data type."""

    model: str
    ram: int
    serial: str
    temperature: int
    temperature_warn: bool
    uptime: int
    version: str
    version_string: str


class SynoDSMInformation(SynoBaseApi[DsmInformationDataType]):
    """Class containing Information data."""

    API_KEY = "SYNO.DSM.Info"

    async def update(self) -> None:
        """Updates information data."""
        raw_data = await self._dsm.get(self.API_KEY, "getinfo")
        if isinstance(raw_data, dict) and (data := raw_data.get("data")) is not None:
            self._data = data

    @property
    def model(self) -> str:
        """Model of the NAS."""
        return self._data["model"]

    @property
    def ram(self) -> int:
        """RAM of the NAS (in MB)."""
        return self._data["ram"]

    @property
    def serial(self) -> str:
        """Serial of the NAS."""
        return self._data["serial"]

    @property
    def temperature(self) -> int:
        """Temperature of the NAS."""
        return self._data["temperature"]

    @property
    def temperature_warn(self) -> bool:
        """Temperature warning of the NAS."""
        # some very old nas may not provide this attribute
        return self._data.get("temperature_warn", False)

    @property
    def uptime(self) -> int:
        """Uptime of the NAS."""
        return self._data["uptime"]

    @property
    def version(self) -> str:
        """Version of the NAS (build version)."""
        return self._data["version"]

    @property
    def version_string(self) -> str:
        """Version of the NAS."""
        return self._data["version_string"]
