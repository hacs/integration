"""DSM Storage data."""

from __future__ import annotations

from typing import TypedDict, cast

from synology_dsm.api import SynoBaseApi
from synology_dsm.helpers import SynoFormatHelper


class SynoStorageDisk(TypedDict, total=False):
    """Synology Storage Disk."""

    id: str
    name: str
    device: str
    firm: str
    diskType: str  # noqa: N815
    smart_status: str
    status: str
    exceed_bad_sector_thr: bool
    below_remain_life_thr: bool
    temp: int
    model: str
    vendor: str
    size_total: int


SynoStoragePoolChild = TypedDict(
    "SynoStoragePoolChild", {"id": str, "size": dict}, total=False
)


class SynoStoragePool(TypedDict, total=False):
    """Synology Storage Pool."""

    disks: list[str]
    pool_child: list[SynoStoragePoolChild]


SynoStorageVolumeSize = TypedDict(
    "SynoStorageVolumeSize",
    {
        "free_inode": str,
        "total": str,
        "total_device": str,
        "total_inode": str,
        "used": str,
    },
)


class SynoStorageVolume(TypedDict, total=False):
    """Synology Storage Volume."""

    id: str
    device_type: str
    size: SynoStorageVolumeSize
    status: str
    fs_type: str


class StorageDataType(TypedDict, total=False):
    """Synology Storage Data type."""

    disks: list[SynoStorageDisk]
    env: dict
    storagePools: list[SynoStoragePool]  # noqa: N815
    volumes: list[SynoStorageVolume]


class SynoStorage(SynoBaseApi[StorageDataType]):
    """Class containing Storage data."""

    API_KEY = "SYNO.Storage.CGI.Storage"

    async def update(self) -> None:
        """Updates storage data."""
        raw_data = await self._dsm.get(self.API_KEY, "load_info")
        if isinstance(raw_data, dict):
            self._data = cast(StorageDataType, raw_data)
            if (data := raw_data.get("data")) is not None:
                self._data = data

    # Root
    @property
    def disks(self) -> list[SynoStorageDisk]:
        """Gets all (internal) disks."""
        return self._data.get("disks", [])

    @property
    def env(self) -> dict | None:
        """Gets storage env."""
        return self._data.get("env")

    @property
    def storage_pools(self) -> list[SynoStoragePool]:
        """Gets all storage pools."""
        return self._data.get("storagePools", [])

    @property
    def volumes(self) -> list[SynoStorageVolume]:
        """Gets all volumes."""
        return self._data.get("volumes", [])

    # Volume
    @property
    def volumes_ids(self) -> list[str]:
        """Returns volumes ids."""
        volumes: list[str] = []
        for volume in self.volumes:
            volumes.append(volume["id"])
        return volumes

    def get_volume(self, volume_id: str) -> SynoStorageVolume | None:
        """Returns a specific volume."""
        for volume in self.volumes:
            if volume["id"] == volume_id:
                return volume
        return None

    def volume_status(self, volume_id: str) -> str | None:
        """Status of the volume (normal, degraded, etc)."""
        if volume := self.get_volume(volume_id):
            return volume.get("status")
        return None

    def volume_device_type(self, volume_id: str) -> str | None:
        """Returns the volume type (RAID1, RAID2, etc)."""
        if volume := self.get_volume(volume_id):
            return volume.get("device_type")
        return None

    def volume_size_total(
        self, volume_id: str, human_readable: bool = False
    ) -> int | str | None:
        """Total size of volume."""
        if (volume := self.get_volume(volume_id)) is None or (
            size := volume.get("size")
        ) is None:
            return None
        return_data = int(size["total"])
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(return_data)
        return return_data

    def volume_size_used(
        self, volume_id: str, human_readable: bool = False
    ) -> int | str | None:
        """Total used size in volume."""
        if (volume := self.get_volume(volume_id)) is None or (
            size := volume.get("size")
        ) is None:
            return None
        return_data = int(size["used"])
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(return_data)
        return return_data

    def volume_percentage_used(self, volume_id: str) -> float | None:
        """Total used size in percentage for volume."""
        if (volume := self.get_volume(volume_id)) is None or (
            size := volume.get("size")
        ) is None:
            return None
        total = int(size["total"])
        used = int(size["used"])
        return round((float(used) / float(total)) * 100.0, 1)

    def volume_disk_temp_avg(self, volume_id: str) -> float | None:
        """Average temperature of all disks making up the volume."""
        total_temp = 0
        total_disks = 0
        disks = self._get_disks_for_volume(volume_id)
        for disk in disks:
            if disk_temp := self.disk_temp(disk["id"]):
                total_disks += 1
                total_temp += disk_temp

        if total_temp > 0 and total_disks > 0:
            return round(total_temp / total_disks, 0)
        return None

    def volume_disk_temp_max(self, volume_id: str) -> int | None:
        """Maximum temperature of all disks making up the volume."""
        disks = self._get_disks_for_volume(volume_id)
        if not disks:
            return None

        disk_temps: list[int] = [0]
        for disk in disks:
            if disk_temp := self.disk_temp(disk["id"]):
                disk_temps.append(disk_temp)
        return max(disk_temps)

    # Disk
    @property
    def disks_ids(self) -> list[str]:
        """Returns (internal) disks ids."""
        disks: list[str] = []
        for disk in self.disks:
            disks.append(disk["id"])
        return disks

    def get_disk(self, disk_id: str) -> SynoStorageDisk | None:
        """Returns a specific disk."""
        for disk in self.disks:
            if disk["id"] == disk_id:
                return disk
        return None

    def _get_disks_for_volume(self, volume_id: str) -> list[SynoStorageDisk]:
        """Returns a list of disk for a specific volume."""
        disks: list[SynoStorageDisk] = []
        for pool in self.storage_pools:
            if pool.get("deploy_path") == volume_id:
                # RAID disk redundancy
                for disk_id in pool["disks"]:
                    if disk := self.get_disk(disk_id):
                        disks.append(disk)

            if pool.get("pool_child"):
                # SHR disk redundancy
                for pool_child in pool["pool_child"]:
                    if pool_child["id"] != volume_id:
                        continue
                    for disk_id in pool["disks"]:
                        if disk := self.get_disk(disk_id):
                            disks.append(disk)

        return disks

    def disk_name(self, disk_id: str) -> str | None:
        """The name of this disk."""
        if disk := self.get_disk(disk_id):
            return disk.get("name")
        return None

    def disk_device(self, disk_id: str) -> str | None:
        """The mount point of this disk."""
        if disk := self.get_disk(disk_id):
            return disk.get("device")
        return None

    def disk_smart_status(self, disk_id: str) -> str | None:
        """Status of disk according to S.M.A.R.T)."""
        if disk := self.get_disk(disk_id):
            return disk.get("smart_status")
        return None

    def disk_status(self, disk_id: str) -> str | None:
        """Status of disk."""
        if disk := self.get_disk(disk_id):
            return disk.get("status")
        return None

    def disk_exceed_bad_sector_thr(self, disk_id: str) -> bool | None:
        """Checks if disk has exceeded maximum bad sector threshold."""
        if disk := self.get_disk(disk_id):
            return disk.get("exceed_bad_sector_thr")
        return None

    def disk_below_remain_life_thr(self, disk_id: str) -> bool | None:
        """Checks if disk has fallen below minimum life threshold."""
        if disk := self.get_disk(disk_id):
            return disk.get("below_remain_life_thr")
        return None

    def disk_temp(self, disk_id: str) -> int | None:
        """Returns the temperature of the disk."""
        if disk := self.get_disk(disk_id):
            return disk.get("temp")
        return None
