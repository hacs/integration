"""SurveillanceStation camera."""

from __future__ import annotations

from typing import TypedDict

from .const import MOTION_DETECTION_DISABLED, RECORDING_STATUS

SynoCameraData = TypedDict(
    "SynoCameraData",
    {
        "enabled": bool,
        "fps": int,
        "id": int,
        "MDParam": dict,
        "model": str,
        "name": str,
        "recStatus": int,
        "resolution": str,
    },
    total=False,
)

SynoCameraLifeViewData = TypedDict(
    "SynoCameraLifeViewData",
    {
        "mjpegHttpPath": str,
        "multicstPath": str,
        "mxpegHttpPath": str,
        "rtspOverHttpPath": str,
        "rtspPath": str,
    },
    total=False,
)


class SynoCamera:
    """An representation of a Synology SurveillanceStation camera."""

    def __init__(
        self, data: SynoCameraData, live_view_data: SynoCameraLifeViewData | None = None
    ) -> None:
        """Initialize a Surveillance Station camera."""
        self._data: SynoCameraData = data
        self.live_view = SynoCameraLiveView(live_view_data)
        self._motion_detection_enabled: bool | None = None

    def update(self, data: SynoCameraData) -> None:
        """Update the camera."""
        self._data = data

    def update_motion_detection(self, data: SynoCameraData) -> None:
        """Update the camera motion detection."""
        self._motion_detection_enabled = (
            MOTION_DETECTION_DISABLED != data["MDParam"]["source"]
        )

    @property
    def id(self) -> int:
        """Return id of the camera."""
        return self._data["id"]

    @property
    def name(self) -> str:
        """Return name of the camera."""
        return self._data["name"]

    @property
    def model(self) -> str:
        """Return model of the camera."""
        return self._data["model"]

    @property
    def resolution(self) -> str:
        """Return resolution of the camera."""
        return self._data["resolution"]

    @property
    def fps(self) -> int:
        """Return FPS of the camera."""
        return self._data["fps"]

    @property
    def is_enabled(self) -> bool:
        """Return true if camera is enabled."""
        return self._data["enabled"]

    @property
    def is_motion_detection_enabled(self) -> bool | None:
        """Return true if motion detection is enabled."""
        return self._motion_detection_enabled

    @property
    def is_recording(self) -> bool:
        """Return true if camera is recording."""
        return self._data["recStatus"] in RECORDING_STATUS


class SynoCameraLiveView:
    """An representation of a Synology SurveillanceStation camera live view."""

    def __init__(self, data: SynoCameraLifeViewData | None):
        """Initialize a Surveillance Station camera live view."""
        if data is not None:
            self._data = data
        else:
            self._data = {}

    def update(self, data: SynoCameraLifeViewData) -> None:
        """Update the camera live view."""
        self._data = data

    @property
    def mjpeg_http(self) -> str | None:
        """Return the mjpeg stream (over http) path of the camera."""
        return self._data.get("mjpegHttpPath")

    @property
    def multicast(self) -> str | None:
        """Return the multi-cast path of the camera."""
        return self._data.get("multicstPath")

    @property
    def mxpeg_http(self) -> str | None:
        """Return the mxpeg stream path of the camera."""
        return self._data.get("mxpegHttpPath")

    @property
    def rtsp_http(self) -> str | None:
        """Return the RTSP stream (over http) path of the camera."""
        return self._data.get("rtspOverHttpPath")

    @property
    def rtsp(self) -> str | None:
        """Return the RTSP stream path of the camera."""
        return self._data.get("rtspPath")
