"""For HA varios tools."""
import asyncio
import logging
import re
from typing import Optional

from .core import HAFFmpeg
from .timeout import asyncio_timeout

_LOGGER = logging.getLogger(__name__)

IMAGE_JPEG = "mjpeg"
IMAGE_PNG = "png"


class ImageFrame(HAFFmpeg):
    """Implement a single image capture from a stream."""

    async def get_image(
        self,
        input_source: str,
        output_format: str = IMAGE_JPEG,
        extra_cmd: Optional[str] = None,
        timeout: int = 15,
    ) -> Optional[bytes]:
        """Open FFmpeg process as capture 1 frame."""
        command = ["-an", "-frames:v", "1", "-c:v", output_format]

        # open input for capture 1 frame
        is_open = await self.open(
            cmd=command,
            input_source=input_source,
            output="-f image2pipe -",
            extra_cmd=extra_cmd,
        )

        # error after open?
        if not is_open:
            _LOGGER.warning("Error starting FFmpeg.")
            return None

        # read image

        try:
            async with asyncio_timeout(timeout):
                image, _ = await self._proc.communicate()
            return image

        except (asyncio.TimeoutError, ValueError):
            _LOGGER.warning("Timeout reading image.")
            self.kill()
            return None


class FFVersion(HAFFmpeg):
    """Retrieve FFmpeg version information."""

    async def get_version(self, timeout: int = 15) -> Optional[str]:
        """Execute FFmpeg process and parse the version information.

        Return full FFmpeg version string. Such as 3.4.2-tessus
        """
        command = ["-version"]
        # open input for capture 1 frame

        is_open = await self.open(cmd=command, input_source=None, output="")

        # error after open?
        if not is_open:
            _LOGGER.warning("Error starting FFmpeg.")
            return

        # read output
        try:
            async with asyncio_timeout(timeout):
                output, _ = await self._proc.communicate()

            result = re.search(r"ffmpeg version (\S*)", output.decode())
            if result is not None:
                return result.group(1)

        except (asyncio.TimeoutError, ValueError):
            _LOGGER.warning("Timeout reading stdout.")
            self.kill()

        return None
