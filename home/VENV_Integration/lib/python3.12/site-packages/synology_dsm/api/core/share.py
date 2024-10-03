"""Shared Folders data."""

from __future__ import annotations

from typing import TypedDict

from synology_dsm.api import SynoBaseApi
from synology_dsm.helpers import SynoFormatHelper

Share = TypedDict(
    "Share",
    {
        "uuid": str,
        "name": str,
        "vol_path": str,
        "enable_recycle_bin": bool,
        "share_quota_used": float,
    },
    total=False,
)


class ShareDataType(TypedDict):
    """Data type."""

    shares: list[Share]


class SynoCoreShare(SynoBaseApi[ShareDataType]):
    """Class containing Share data."""

    API_KEY = "SYNO.Core.Share"
    # Syno supports two methods to retrieve resource details, GET and POST.
    # GET returns a limited set of keys. With POST the same keys as GET
    # are returned plus any keys listed in the "additional" parameter.
    # NOTE: The value of the additional key must be a string.
    REQUEST_DATA = {
        "additional": '["hidden","encryption","is_aclmode","unite_permission",'
        '"is_support_acl","is_sync_share","is_force_readonly","force_readonly_reason",'
        '"recyclebin","is_share_moving","is_cluster_share","is_exfat_share",'
        '"is_cold_storage_share","support_snapshot","share_quota",'
        '"enable_share_compress","enable_share_cow","include_cold_storage_share",'
        '"is_cold_storage_share"]',
        "shareType": "all",
    }

    async def update(self) -> None:
        """Updates share data."""
        raw_data = await self._dsm.post(self.API_KEY, "list", data=self.REQUEST_DATA)
        if isinstance(raw_data, dict) and (data := raw_data.get("data")) is not None:
            self._data = data

    @property
    def shares(self) -> list[Share]:
        """Gets all shares."""
        return self._data["shares"]

    @property
    def shares_uuids(self) -> list[str]:
        """Return (internal) share ids."""
        shares = []
        for share in self.shares:
            shares.append(share["uuid"])
        return shares

    def get_share(self, share_uuid: str) -> Share:
        """Returns a specific share by uuid.."""
        for share in self.shares:
            if share["uuid"] == share_uuid:
                return share
        return {}

    def share_name(self, share_uuid: str) -> str:
        """Return the name of this share."""
        return self.get_share(share_uuid)["name"]

    def share_path(self, share_uuid: str) -> str:
        """Return the volume path of this share."""
        return self.get_share(share_uuid)["vol_path"]

    def share_recycle_bin(self, share_uuid: str) -> bool:
        """Is the recycle bin enabled for this share?"""
        return self.get_share(share_uuid)["enable_recycle_bin"]

    def share_size(self, share_uuid: str, human_readable: bool = False) -> int | str:
        """Total size of share."""
        share_size_mb = self.get_share(share_uuid)["share_quota_used"]
        # Share size is returned in MB so we convert it.
        share_size_bytes = SynoFormatHelper.megabytes_to_bytes(share_size_mb)
        if human_readable:
            return SynoFormatHelper.bytes_to_readable(share_size_bytes)
        return share_size_bytes
