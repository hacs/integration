"""For HA camera components."""
from typing import Coroutine, Optional

from .core import HAFFmpeg


class CameraMjpeg(HAFFmpeg):
    """Implement a camera they convert video stream to MJPEG."""

    def open_camera(
        self, input_source: str, extra_cmd: Optional[str] = None
    ) -> Coroutine:
        """Open FFmpeg process as mjpeg video stream.

        Return A coroutine.
        """
        command = ["-an", "-c:v", "mjpeg"]

        return self.open(
            cmd=command,
            input_source=input_source,
            output="-f mpjpeg -",
            extra_cmd=extra_cmd,
        )
