"""DSM Security data."""

from __future__ import annotations

from typing import TypedDict

from synology_dsm.api import SynoBaseApi

SecurityCategory = TypedDict(
    "SecurityCategory",
    {
        "category": str,
        "fail": "dict[str, int]",
        "failSeverity": str,
        "progress": int,
        "runningItem": str,
        "total": int,
        "waitNum": int,
    },
)


class SecurityDataType(TypedDict):
    """Data type."""

    items: dict[str, SecurityCategory]
    lastScanTime: str  # noqa: N815
    startTime: str  # noqa: N815
    success: bool
    sysProgress: int  # noqa: N815
    sysStatus: str  # noqa: N815


class SynoCoreSecurity(SynoBaseApi[SecurityDataType]):
    """Class containing Security data."""

    API_KEY = "SYNO.Core.SecurityScan.Status"

    async def update(self) -> None:
        """Updates security data."""
        raw_data = await self._dsm.get(self.API_KEY, "system_get")
        if isinstance(raw_data, dict) and (data := raw_data.get("data")) is not None:
            self._data = data

    @property
    def checks(self) -> dict[str, SecurityCategory]:
        """Gets the checklist by check category."""
        return self._data["items"]

    @property
    def last_scan_time(self) -> str:
        """Gets the last scan time."""
        return self._data["lastScanTime"]

    @property
    def start_time(self) -> str:
        """Gets the start time (if in progress)."""
        return self._data["startTime"]

    @property
    def success(self) -> bool:
        """Gets the last scan success."""
        return self._data["success"]

    @property
    def progress(self) -> int:
        """Gets the scan progress.

        Returns: 100 if finished
        """
        return self._data["sysProgress"]

    @property
    def status(self) -> str:
        """Gets the last scan status.

        Possible values: safe, danger, info, outOfDate, risk, warning.
        """
        return self._data["sysStatus"]

    @property
    def status_by_check(self) -> dict[str, str]:
        """Gets the last scan status per check."""
        status = {}
        for category in self.checks:
            status[category] = self.checks[category]["failSeverity"]
        return status
