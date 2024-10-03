"""DSM external USB device data."""

from __future__ import annotations

from typing import TypedDict, cast

from synology_dsm.api import SynoBaseApi
from synology_dsm.helpers import SynoFormatHelper

ExternalUsbDevicePartitionDataType = TypedDict(
    "ExternalUsbDevicePartitionDataType",
    {
        "dev_fstype": str,
        "filesystem": str,
        "name_id": str,
        "partition_title": str,
        "share_name": str,
        "status": str,
        "total_size_mb": "int | str",
        "used_size_mb": "int | None",
    },
    total=False,
)
ExternalUsbDeviceDataType = TypedDict(
    "ExternalUsbDeviceDataType",
    {
        "dev_id": str,
        "dev_title": str,
        "dev_type": str,
        "formatable": bool,
        "partitions": "dict[str, SynoUSBStoragePartition]",
        "producer": str,
        "product": str,
        "progress": str,
        "status": str,
        "total_size_mb": int,
    },
    total=False,
)


class SynoCoreExternalUSB(SynoBaseApi["dict[str, SynoCoreExternalUSBDevice]"]):
    """Class for external USB storage devices."""

    API_KEY = "SYNO.Core.ExternalDevice.Storage.USB"
    REQUEST_DATA = {"additional": '["all"]'}

    async def update(self) -> None:
        """Updates external USB storage device data."""
        raw_data = await self._dsm.post(self.API_KEY, "list", data=self.REQUEST_DATA)
        if isinstance(raw_data, dict) and (data := raw_data.get("data")) is not None:
            for device in data["devices"]:
                self._data[device["dev_id"]] = SynoCoreExternalUSBDevice(device)

    # Root
    @property
    def get_devices(self) -> dict[str, SynoCoreExternalUSBDevice]:
        """Gets all external USB storage devices."""
        return self._data

    def get_device(self, device_id: str) -> SynoCoreExternalUSBDevice | None:
        """Returns a specific external USB storage device."""
        return self._data.get(device_id)


class SynoCoreExternalUSBDevice:
    """A representation of an external USB device."""

    def __init__(self, data: dict):
        """Initialize a external USB device."""
        partitions: dict[str, SynoUSBStoragePartition] = {}
        for partition in data["partitions"]:
            partitions[partition["name_id"]] = SynoUSBStoragePartition(partition)
        self._data = cast(ExternalUsbDeviceDataType, {**data, "partitions": partitions})

    @property
    def device_id(self) -> str:
        """Return id of the device."""
        return self._data["dev_id"]

    @property
    def device_name(self) -> str:
        """The title of the external USB storage device."""
        return self._data["dev_title"]

    @property
    def device_type(self) -> str:
        """The type of the external USB storage device."""
        return self._data["dev_type"]

    def device_size_total(self, human_readable: bool = False) -> str | int:
        """Total size of the external USB storage device."""
        return_data = SynoFormatHelper.megabytes_to_bytes(
            int(self._data["total_size_mb"])
        )
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(return_data)
        return return_data

    @property
    def device_status(self) -> str:
        """The status of the external USB storage device."""
        return self._data["status"]

    @property
    def device_formatable(self) -> bool:
        """Whether the external USB storage device can be formatted."""
        return self._data["formatable"]

    @property
    def device_progress(self) -> str:
        """The progress the external USB storage device."""
        return self._data["progress"]

    @property
    def device_product_name(self) -> str:
        """The product name of the external USB storage device."""
        return self._data["product"]

    @property
    def device_manufacturer(self) -> str:
        """The producer name of the external USB storage device."""
        return self._data["producer"]

    # Partition
    @property
    def device_partitions(self) -> dict[str, SynoUSBStoragePartition]:
        """Returns all partitions of the external USB storage device."""
        return self._data["partitions"]

    def get_device_partition(self, partition_id: str) -> SynoUSBStoragePartition | None:
        """Returns a partition of the external USB storage device."""
        return self._data["partitions"].get(partition_id)

    def partitions_all_size_total(
        self, human_readable: bool = False
    ) -> str | int | None:
        """Total size of all parititions of the external USB storage device."""
        partitions = self._data["partitions"]
        if not partitions:
            return None

        size_total = 0
        for partition in partitions.values():
            partition_size = partition.partition_size_total()
            # Partitions may be reported without a size
            if isinstance(partition_size, int):
                size_total += partition_size

        if human_readable:
            return SynoFormatHelper.bytes_to_readable(size_total)
        return size_total

    def partitions_all_size_used(
        self, human_readable: bool = False
    ) -> str | int | None:
        """Total size used of all partitions of the external USB storage device."""
        partitions = self._data["partitions"]
        if not partitions:
            return None

        size_used = 0
        for partition in partitions.values():
            partition_used = partition.partition_size_used()
            # Partitions may be reported without a size
            if isinstance(partition_used, int):
                size_used += partition_used

        if human_readable:
            return SynoFormatHelper.bytes_to_readable(size_used)
        return size_used

    @property
    def partitions_all_percentage_used(self) -> float | None:
        """Used size in percentage for all partitions of the USB storage device."""
        size_total = self.partitions_all_size_total()
        size_used = self.partitions_all_size_used()

        if (
            isinstance(size_used, int)
            and size_used >= 0
            and isinstance(size_total, int)
            and size_total > 0
        ):
            return round((float(size_used) / float(size_total)) * 100.0, 1)
        return None


class SynoUSBStoragePartition:
    """A representation of a parition of an external USB storage device."""

    def __init__(self, data: ExternalUsbDevicePartitionDataType):
        """Initialize a partition object of an external USB storage device."""
        self._data = data

    @property
    def fstype(self) -> str:
        """Return the dev_fstype for the partition."""
        return self._data["dev_fstype"]

    @property
    def filesystem(self) -> str:
        """Return the filesystem for the partition."""
        return self._data["filesystem"]

    @property
    def name_id(self) -> str:
        """Return the name_id for the partition."""
        return self._data["name_id"]

    @property
    def partition_title(self) -> str:
        """Return the title for the partition."""
        return self._data["partition_title"]

    @property
    def share_name(self) -> str:
        """Return the share name for the partition."""
        return self._data["share_name"]

    @property
    def status(self) -> str:
        """Return the status for the partition."""
        return self._data["status"]

    def partition_size_total(self, human_readable: bool = False) -> int | str | None:
        """Total size of the partition."""
        # API returns property as empty string if a partition has no size
        size_total = self._data["total_size_mb"]
        if not isinstance(size_total, int):
            return None
        size_total = SynoFormatHelper.megabytes_to_bytes(size_total)
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(size_total)
        return size_total

    def partition_size_used(self, human_readable: bool = False) -> int | str | None:
        """Used size of the partition."""
        # API does not return property if a partition has no size
        size_used = self._data.get("used_size_mb")
        if not isinstance(size_used, int):
            return None
        size_used = SynoFormatHelper.megabytes_to_bytes(size_used)
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(size_used)
        return size_used

    @property
    def partition_percentage_used(self) -> float | None:
        """Used size in percentage of the partition."""
        size_total = self.partition_size_total()
        size_used = self.partition_size_used()
        if (
            isinstance(size_used, int)
            and size_used >= 0
            and isinstance(size_total, int)
            and size_total > 0
        ):
            return round((float(size_used) / float(size_total)) * 100.0, 1)
        return None

    @property
    def is_mounted(self) -> bool:
        """Is the partition formatted."""
        return self._data["share_name"] != ""

    @property
    def is_supported(self) -> bool:
        """Is the partition formatted."""
        return self._data["filesystem"] != ""
