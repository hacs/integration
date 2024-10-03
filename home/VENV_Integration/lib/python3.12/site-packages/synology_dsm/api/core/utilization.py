"""DSM Utilization data."""

from __future__ import annotations

from typing import TypedDict

from synology_dsm.api import SynoBaseApi
from synology_dsm.helpers import SynoFormatHelper

CpuUtilization = TypedDict(
    "CpuUtilization",
    {
        "15min_load": int,
        "1min_load": int,
        "5min_load": int,
        "device": str,
        "other_load": int,
        "system_load": int,
        "user_load": int,
    },
)

MemoryUtilization = TypedDict(
    "MemoryUtilization",
    {
        "avail_real": int,
        "avail_swap": int,
        "buffer": int,
        "cached": int,
        "device": str,
        "memory_size": int,
        "real_usage": int,
        "si_disk": int,
        "so_disk": int,
        "swap_usage": int,
        "total_real": int,
        "total_swap": int,
    },
)

NetworkUtilization = TypedDict(
    "NetworkUtilization",
    {
        "device": str,
        "rx": int,
        "tx": int,
    },
)


class UtilizationDataType(TypedDict, total=False):
    """Data type."""

    cpu: CpuUtilization
    memory: MemoryUtilization
    network: list[NetworkUtilization]


class SynoCoreUtilization(SynoBaseApi[UtilizationDataType]):
    """Class containing Utilization data."""

    API_KEY = "SYNO.Core.System.Utilization"

    async def update(self) -> None:
        """Updates utilization data."""
        raw_data = await self._dsm.get(self.API_KEY, "get")
        if isinstance(raw_data, dict) and (data := raw_data.get("data")) is not None:
            self._data = data

    @property
    def cpu(self) -> CpuUtilization:
        """Gets CPU utilization."""
        return self._data["cpu"]

    @property
    def cpu_other_load(self) -> int:
        """Other percentage of the total CPU load."""
        return self.cpu["other_load"]

    @property
    def cpu_user_load(self) -> int:
        """User percentage of the total CPU load."""
        return self.cpu["user_load"]

    @property
    def cpu_system_load(self) -> int:
        """System percentage of the total CPU load."""
        return self.cpu["system_load"]

    @property
    def cpu_total_load(self) -> int:
        """Total CPU load for Synology DSM."""
        system_load = self.cpu_system_load
        user_load = self.cpu_user_load
        other_load = self.cpu_other_load

        return system_load + user_load + other_load

    @property
    def cpu_1min_load(self) -> int:
        """Average CPU load past minute."""
        return self.cpu["1min_load"]

    @property
    def cpu_5min_load(self) -> int:
        """Average CPU load past 5 minutes."""
        return self.cpu["5min_load"]

    @property
    def cpu_15min_load(self) -> int:
        """Average CPU load past 15 minutes."""
        return self.cpu["15min_load"]

    @property
    def memory(self) -> MemoryUtilization:
        """Gets memory utilization."""
        return self._data["memory"]

    @property
    def memory_real_usage(self) -> int:
        """Real Memory usage from Synology DSM."""
        return self.memory["real_usage"]

    def memory_size(self, human_readable: bool = False) -> int | str:
        """Total memory size of Synology DSM."""
        return_data = self.memory["memory_size"] * 1024
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(return_data)
        return return_data

    def memory_available_swap(self, human_readable: bool = False) -> int | str:
        """Total available memory swap."""
        # Memory is actually returned in KB's so multiply before converting
        return_data = self.memory["avail_swap"] * 1024
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(return_data)
        return return_data

    def memory_cached(self, human_readable: bool = False) -> int | str:
        """Total cached memory."""
        # Memory is actually returned in KB's so multiply before converting
        return_data = self.memory["cached"] * 1024
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(return_data)
        return return_data

    def memory_available_real(self, human_readable: bool = False) -> int | str:
        """Real available memory."""
        # Memory is actually returned in KB's so multiply before converting
        return_data = self.memory["avail_real"] * 1024
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(return_data)
        return return_data

    def memory_total_real(self, human_readable: bool = False) -> int | str:
        """Total available real memory."""
        # Memory is actually returned in KB's so multiply before converting
        return_data = self.memory["total_real"] * 1024
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(return_data)
        return return_data

    def memory_total_swap(self, human_readable: bool = False) -> int | str:
        """Total swap memory."""
        # Memory is actually returned in KB's so multiply before converting
        return_data = self.memory["total_swap"] * 1024
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(return_data)
        return return_data

    @property
    def network(self) -> list[NetworkUtilization]:
        """Gets network utilization."""
        return self._data["network"]

    def _get_network(self, network_id: str) -> NetworkUtilization | None:
        """Function to get specific network (eth0, total, etc)."""
        for network in self.network:
            if network["device"] == network_id:
                return network
        return None

    def network_up(self, human_readable: bool = False) -> int | str | None:
        """Total upload speed being used."""
        if (network := self._get_network("total")) is not None:
            return_data = network["tx"]
            if human_readable:
                return SynoFormatHelper.bytes_to_readable(return_data)
            return return_data
        return None

    def network_down(self, human_readable: bool = False) -> int | str | None:
        """Total download speed being used."""
        if (network := self._get_network("total")) is not None:
            return_data = network["rx"]
            if human_readable:
                return SynoFormatHelper.bytes_to_readable(return_data)
            return return_data
        return None
