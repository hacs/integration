"""Synology SurveillanceStation API wrapper."""

from __future__ import annotations

from typing import TypedDict, cast

from synology_dsm.api import SynoBaseApi

from .camera import SynoCamera, SynoCameraLiveView
from .const import (
    MOTION_DETECTION_BY_SURVEILLANCE,
    MOTION_DETECTION_DISABLED,
    SNAPSHOT_PROFILE_BALANCED,
)

SurveillanceStationInfoData = TypedDict(
    "SurveillanceStationInfoData",
    {
        "CMSMinVersion": str,
        "DSModelName": str,
        "SvsClientMinVersion": str,
        "VS360HDLoginMinVersion": str,
        "VS960HDMinVersion": str,
        "cameraNumber": int,
        "defaultWallpaperCount": int,
        "enableVideoRelay": bool,
        "hostname": str,
        "inaAdvancedPriv": int,
        "isBeta": bool,
        "isLicenseEnough": int,
        "is_beta": bool,
        "liscenseNumber": int,
        "maxCameraSupport": int,
        "maxlanport": str,
        "path": str,
        "pluginHelperVersion": str,
        "productName": str,
        "remindQuickconnectTunnel": bool,
        "reportURL": str,
        "serial": str,
        "serviceVolSize": float,
        "strInaAdvancedPriv": str,
        "timezone": str,
        "timezoneTZDB": str,
        "uid": int,
        "unique": str,
        "userPriv": int,
        "version": dict,
        "webPluginVersion": str,
    },
    total=False,
)

SurveillanceStationInfo = TypedDict(
    "SurveillanceStationInfo", {"data": SurveillanceStationInfoData, "success": bool}
)

SurveillanceStationTakeSnapshotDataType = TypedDict(
    "SurveillanceStationTakeSnapshotDataType", {"id": int}
)

SurveillanceStationTakeSnapshotType = TypedDict(
    "SurveillanceStationTakeSnapshotType",
    {"data": SurveillanceStationTakeSnapshotDataType, "success": bool},
)


class SynoSurveillanceStation(SynoBaseApi["dict[int, SynoCamera]"]):
    """An implementation of a Synology SurveillanceStation."""

    API_KEY = "SYNO.SurveillanceStation.*"
    INFO_API_KEY = "SYNO.SurveillanceStation.Info"
    CAMERA_API_KEY = "SYNO.SurveillanceStation.Camera"
    CAMERA_EVENT_API_KEY = "SYNO.SurveillanceStation.Camera.Event"
    HOME_MODE_API_KEY = "SYNO.SurveillanceStation.HomeMode"
    SNAPSHOT_API_KEY = "SYNO.SurveillanceStation.SnapShot"

    async def update(self) -> None:
        """Update cameras and motion settings with latest from API."""
        self._data: dict[int, SynoCamera] = {}
        raw_data = await self._dsm.get(self.CAMERA_API_KEY, "List", max_version=7)
        if not isinstance(raw_data, dict) or (data := raw_data.get("data")) is None:
            return

        for camera_data in data["cameras"]:
            if camera_data["id"] in self._data:
                self._data[camera_data["id"]].update(camera_data)
            else:
                self._data[camera_data["id"]] = SynoCamera(camera_data)

        for camera_id, camera in self._data.items():
            motion_raw_data = await self._dsm.get(
                self.CAMERA_EVENT_API_KEY, "MotionEnum", {"camId": camera_id}
            )
            if (
                isinstance(motion_raw_data, dict)
                and (motion_data := motion_raw_data.get("data")) is not None
            ):
                camera.update_motion_detection(motion_data)

        if not self._data:
            return

        live_view_raw_datas = await self._dsm.get(
            self.CAMERA_API_KEY,
            "GetLiveViewPath",
            {"idList": ",".join(str(k) for k in self._data)},
        )
        if (
            isinstance(live_view_raw_datas, dict)
            and (live_view_datas := live_view_raw_datas.get("data")) is not None
        ):
            for live_view_data in live_view_datas:
                self._data[live_view_data["id"]].live_view.update(live_view_data)

    # Global
    async def get_info(self) -> SurveillanceStationInfo | None:
        """Return general informations about the Surveillance Station instance."""
        raw_data = await self._dsm.get(self.INFO_API_KEY, "GetInfo")
        if isinstance(raw_data, dict) and raw_data.get("success"):
            return cast(SurveillanceStationInfo, raw_data)
        return None

    # Camera
    def get_all_cameras(self) -> list[SynoCamera]:
        """Return a list of cameras."""
        return list(self._data.values())

    def get_camera(self, camera_id: int) -> SynoCamera | None:
        """Return camera matching camera_id."""
        return self._data.get(camera_id)

    def get_camera_live_view_path(
        self, camera_id: int, video_format: str | None = None
    ) -> SynoCameraLiveView | str | None:
        """Return camera live view path matching camera_id.

        Args:
            camera_id: ID of the camera we want to get the live view path.
            video_format: mjpeg_http | multicast | mxpeg_http |  rtsp_http | rtsp.
        """
        if (camera := self._data.get(camera_id)) is None:
            return None
        if video_format:
            return getattr(camera.live_view, video_format, None)
        return camera.live_view

    async def get_camera_image(
        self, camera_id: int, profile: int = SNAPSHOT_PROFILE_BALANCED
    ) -> bytes:
        """Return bytes of camera image for camera matching camera_id.

        Args:
            camera_id: ID of the camera we want to take a snapshot from
            profile: SNAPSHOT_PROFILE_HIGH_QUALITY |
                     SNAPSHOT_PROFILE_BALANCED |
                     SNAPSHOT_PROFILE_LOW_BANDWIDTH
        """
        return cast(
            bytes,
            await self._dsm.get(
                self.CAMERA_API_KEY,
                "GetSnapshot",
                {"id": camera_id, "cameraId": camera_id, "profileType": profile},
            ),
        )

    async def enable_camera(self, camera_ids: str) -> bool | None:
        """Enable camera(s) - multiple ID or single ex 1 or 1,2,3."""
        raw_data = await self._dsm.get(
            self.CAMERA_API_KEY, "Enable", {"idList": camera_ids}
        )
        if (
            isinstance(raw_data, dict)
            and (result := raw_data.get("success")) is not None
        ):
            return bool(result)
        return None

    async def disable_camera(self, camera_ids: str) -> bool | None:
        """Disable camera(s) - multiple ID or single ex 1 or 1,2,3."""
        raw_data = await self._dsm.get(
            self.CAMERA_API_KEY, "Disable", {"idList": camera_ids}
        )
        if (
            isinstance(raw_data, dict)
            and (result := raw_data.get("success")) is not None
        ):
            return bool(result)
        return None

    # Snapshot
    async def capture_camera_image(
        self, camera_id: int, save: bool = True
    ) -> SurveillanceStationTakeSnapshotType | None:
        """Capture a snapshot for camera matching camera_id."""
        raw_data = await self._dsm.get(
            self.SNAPSHOT_API_KEY,
            "TakeSnapshot",
            {
                "camId": camera_id,
                "blSave": int(save),  # API requires an integer instead of a boolean
            },
        )
        if isinstance(raw_data, dict):
            return cast(SurveillanceStationTakeSnapshotType, raw_data)
        return None

    async def download_snapshot(
        self, snapshot_id: int, snapshot_size: int
    ) -> bytes | None:
        """Download snapshot image binary for a givent snapshot_id.

        Args:
            snapshot_id: ID of the snapshot we want to download.
            snapshot_size: SNAPSHOT_SIZE_ICON | SNAPSHOT_SIZE_FULL.
        """
        raw_data = await self._dsm.get(
            self.SNAPSHOT_API_KEY,
            "LoadSnapshot",
            {"id": snapshot_id, "imgSize": snapshot_size},
        )
        if isinstance(raw_data, bytes):
            return raw_data
        return None

    # Motion
    def is_motion_detection_enabled(self, camera_id: int) -> bool:
        """Return motion setting matching camera_id."""
        return bool(self._data[camera_id].is_motion_detection_enabled)

    async def enable_motion_detection(self, camera_id: int) -> dict | None:
        """Enable motion detection for camera matching camera_id."""
        raw_data = await self._dsm.get(
            self.CAMERA_EVENT_API_KEY,
            "MDParamSave",
            {"camId": camera_id, "source": MOTION_DETECTION_BY_SURVEILLANCE},
        )
        if isinstance(raw_data, dict):
            return raw_data
        return None

    async def disable_motion_detection(self, camera_id: int) -> dict | None:
        """Disable motion detection for camera matching camera_id."""
        raw_data = await self._dsm.get(
            self.CAMERA_EVENT_API_KEY,
            "MDParamSave",
            {"camId": camera_id, "source": MOTION_DETECTION_DISABLED},
        )
        if isinstance(raw_data, dict):
            return raw_data
        return None

    # Home mode
    async def get_home_mode_status(self) -> bool | None:
        """Get the state of Home Mode."""
        raw_data = await self._dsm.get(self.HOME_MODE_API_KEY, "GetInfo")
        if (
            isinstance(raw_data, dict)
            and raw_data.get("data")
            and (status := raw_data["data"].get("on")) is not None
        ):
            return bool(status)
        return None

    async def set_home_mode(self, state: bool) -> bool | None:
        """Set the state of Home Mode (state: bool)."""
        raw_data = await self._dsm.get(
            self.HOME_MODE_API_KEY, "Switch", {"on": str(state).lower()}
        )
        if (
            isinstance(raw_data, dict)
            and (result := raw_data.get("success")) is not None
        ):
            return bool(result)
        return None
