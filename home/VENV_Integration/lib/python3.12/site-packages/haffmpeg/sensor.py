"""For HA sensor components."""
import asyncio
import logging
import re
from time import time
from typing import Callable, Coroutine, Optional

from .core import FFMPEG_STDOUT, HAFFmpegWorker
from .timeout import asyncio_timeout

_LOGGER = logging.getLogger(__name__)


class SensorNoise(HAFFmpegWorker):
    """Implement a noise detection on a autio stream."""

    STATE_NONE = 0
    STATE_NOISE = 1
    STATE_END = 2
    STATE_DETECT = 3

    def __init__(self, ffmpeg_bin: str, callback: Callable):
        """Init noise sensor."""
        super().__init__(ffmpeg_bin)

        self._callback = callback
        self._peak = -30
        self._time_duration = 1
        self._time_reset = 2

    def set_options(
        self, time_duration: int = 1, time_reset: int = 2, peak: int = -30
    ) -> None:
        """Set option parameter for noise sensor."""
        self._time_duration = time_duration
        self._time_reset = time_reset
        self._peak = peak

    def open_sensor(
        self,
        input_source: str,
        output_dest: Optional[str] = None,
        extra_cmd: Optional[str] = None,
    ) -> Coroutine:
        """Open FFmpeg process for read autio stream.

        Return a coroutine.
        """
        command = ["-vn", "-filter:a", f"silencedetect=n={self._peak}dB:d=1"]

        # run ffmpeg, read output
        return self.start_worker(
            cmd=command,
            input_source=input_source,
            output=output_dest,
            extra_cmd=extra_cmd,
            pattern="silence",
        )

    async def _worker_process(self) -> None:
        """This function processing data."""
        state = self.STATE_DETECT
        timeout = self._time_duration

        self._loop.call_soon(self._callback, False)

        re_start = re.compile("silence_start")
        re_end = re.compile("silence_end")

        # process queue data
        while True:
            try:
                _LOGGER.debug("Reading State: %d, timeout: %s", state, timeout)
                async with asyncio_timeout(timeout):
                    data = await self._queue.get()
                timeout = None
                if data is None:
                    self._loop.call_soon(self._callback, None)
                    return
            except asyncio.TimeoutError:
                _LOGGER.debug("Blocking timeout")
                # noise
                if state == self.STATE_DETECT:
                    # noise detected
                    self._loop.call_soon(self._callback, True)
                    state = self.STATE_NOISE

                elif state == self.STATE_END:
                    # no noise
                    self._loop.call_soon(self._callback, False)
                    state = self.STATE_NONE

                timeout = None
                continue

            if re_start.search(data):
                if state == self.STATE_NOISE:
                    # stop noise detection
                    state = self.STATE_END
                    timeout = self._time_reset
                elif state == self.STATE_DETECT:
                    # reset if only a peak
                    state = self.STATE_NONE
                continue

            if re_end.search(data):
                if state == self.STATE_NONE:
                    # detect noise begin
                    state = self.STATE_DETECT
                    timeout = self._time_duration
                elif state == self.STATE_END:
                    # back to noise status
                    state = self.STATE_NOISE
                continue

            _LOGGER.warning("Unknown data from queue!")


class SensorMotion(HAFFmpegWorker):
    """Implement motion detection with ffmpeg scene detection."""

    STATE_NONE = 0
    STATE_REPEAT = 1
    STATE_MOTION = 2

    MATCH = r"\d,.*\d,.*\d,.*\d,.*\d,.*\w"

    def __init__(self, ffmpeg_bin: str, callback: Callable):
        """Init motion sensor."""
        super().__init__(ffmpeg_bin)

        self._callback = callback
        self._changes = 10
        self._time_reset = 60
        self._time_repeat = 0
        self._repeat = 0

    def set_options(
        self,
        time_reset: int = 60,
        time_repeat: int = 0,
        repeat: int = 0,
        changes: int = 10,
    ) -> None:
        """Set option parameter for noise sensor."""
        self._time_reset = time_reset
        self._time_repeat = time_repeat
        self._repeat = repeat
        self._changes = changes

    async def open_sensor(
        self, input_source: str, extra_cmd: Optional[str] = None
    ) -> Coroutine:
        """Open FFmpeg process a video stream for motion detection.

        Return a coroutine.
        """
        command = [
            "-an",
            "-filter:v",
            f"select=gt(scene\\,{self._changes / 100})",
        ]

        # run ffmpeg, read output
        return await self.start_worker(
            cmd=command,
            input_source=input_source,
            output="-f framemd5 -",
            extra_cmd=extra_cmd,
            pattern=self.MATCH,
            reading=FFMPEG_STDOUT,
        )

    async def _worker_process(self) -> None:
        """This function processing data."""
        state = self.STATE_NONE
        timeout = None

        self._loop.call_soon(self._callback, False)

        # for repeat feature
        re_frame = 0
        re_time = 0

        re_data = re.compile(self.MATCH)

        # process queue data
        while True:
            try:
                _LOGGER.debug("Reading State: %d, timeout: %s", state, timeout)
                async with asyncio_timeout(timeout):
                    data = await self._queue.get()
                if data is None:
                    self._loop.call_soon(self._callback, None)
                    return
            except asyncio.TimeoutError:
                _LOGGER.debug("Blocking timeout")
                # reset motion detection
                if state == self.STATE_MOTION:
                    state = self.STATE_NONE
                    self._loop.call_soon(self._callback, False)
                    timeout = None
                # reset repeate state
                if state == self.STATE_REPEAT:
                    state = self.STATE_NONE
                    timeout = None
                continue

            frames = re_data.search(data)
            if frames:
                # repeat not used
                if self._repeat == 0 and state == self.STATE_NONE:
                    state = self.STATE_MOTION
                    self._loop.call_soon(self._callback, True)
                    timeout = self._time_reset

                # repeat feature is on / first motion
                if state == self.STATE_NONE:
                    state = self.STATE_REPEAT
                    timeout = self._time_repeat
                    re_frame = 0
                    re_time = time()

                elif state == self.STATE_REPEAT:
                    re_frame += 1

                    # REPEAT ready?
                    if re_frame >= self._repeat:
                        state = self.STATE_MOTION
                        self._loop.call_soon(self._callback, True)
                        timeout = self._time_reset
                    else:
                        past = time() - re_time
                        timeout -= past

                    # REPEAT time down
                    if timeout <= 0:
                        _LOGGER.debug("Reset repeat to none")
                        state = self.STATE_NONE
                        timeout = None

                continue

            _LOGGER.warning("Unknown data from queue!")
