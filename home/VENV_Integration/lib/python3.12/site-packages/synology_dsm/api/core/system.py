"""DSM System data and actions."""

from __future__ import annotations

from typing import Any, TypedDict

from synology_dsm.api import SynoBaseApi


class SystemDataType(TypedDict):
    """Data type."""

    cpu_clock_speed: int
    cpu_cores: str
    cpu_family: str
    cpu_series: str
    enabled_ntp: bool
    ntp_server: str
    firmware_ver: str
    model: str
    ram_size: int
    serial: str
    sys_temp: int
    time: str
    time_zone: str
    time_zone_desc: str
    up_time: str
    usb_dev: list[dict[str, Any]]


class SynoCoreSystem(SynoBaseApi[SystemDataType]):
    """Class containing System data and actions."""

    API_KEY = "SYNO.Core.System"

    async def update(self) -> None:
        """Updates System data."""
        raw_data = await self._dsm.get(self.API_KEY, "info")
        if isinstance(raw_data, dict) and (data := raw_data.get("data")) is not None:
            self._data = data

    #
    # get information
    #
    @property
    def cpu_clock_speed(self) -> int:
        """Gets System CPU clock speed."""
        return self._data["cpu_clock_speed"]

    @property
    def cpu_cores(self) -> str:
        """Gets System CPU cores."""
        return self._data["cpu_cores"]

    @property
    def cpu_family(self) -> str:
        """Gets System CPU family."""
        return self._data["cpu_family"]

    @property
    def cpu_series(self) -> str:
        """Gets System CPU series."""
        return self._data["cpu_series"]

    @property
    def enabled_ntp(self) -> bool:
        """Gets System NTP state."""
        return self._data["enabled_ntp"]

    @property
    def ntp_server(self) -> str:
        """Gets System NTP server."""
        return self._data["ntp_server"]

    @property
    def firmware_ver(self) -> str:
        """Gets System firmware version."""
        return self._data["firmware_ver"]

    @property
    def model(self) -> str:
        """Gets System model."""
        return self._data["model"]

    @property
    def ram_size(self) -> int:
        """Gets System ram size."""
        return self._data["ram_size"]

    @property
    def serial(self) -> str:
        """Gets System serial number."""
        return self._data["serial"]

    @property
    def sys_temp(self) -> int:
        """Gets System temperature."""
        return self._data["sys_temp"]

    @property
    def time(self) -> str:
        """Gets System time."""
        return self._data["time"]

    @property
    def time_zone(self) -> str:
        """Gets System time zone."""
        return self._data["time_zone"]

    @property
    def time_zone_desc(self) -> str:
        """Gets System time zone description."""
        return self._data["time_zone_desc"]

    @property
    def up_time(self) -> str:
        """Gets System uptime."""
        return self._data["up_time"]

    @property
    def usb_dev(self) -> list:
        """Gets System connected usb devices."""
        return self._data["usb_dev"]

    #
    # do system actions
    #
    async def shutdown(self) -> None:
        """Shutdown NAS."""
        await self._dsm.get(
            self.API_KEY,
            "shutdown",
            max_version=1,  # shutdown method is only available on api version 1
        )

    async def reboot(self) -> None:
        """Reboot NAS."""
        await self._dsm.get(
            self.API_KEY,
            "reboot",
            max_version=1,  # reboot method is only available on api version 1
        )
