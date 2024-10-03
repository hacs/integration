"""Base functionality of ffmpeg HA wrapper."""
import asyncio
import logging
import re
import shlex
from typing import List, Optional, Set

from .timeout import asyncio_timeout

_LOGGER = logging.getLogger(__name__)

FFMPEG_STDOUT = "stdout"
FFMPEG_STDERR = "stderr"

_BACKGROUND_TASKS: Set[asyncio.Task] = set()


class HAFFmpeg:
    """HA FFmpeg process async.

    Object is iterable or use the process property to call from Popen object.
    """

    def __init__(self, ffmpeg_bin: str):
        """Base initialize."""
        self._loop = asyncio.get_running_loop()
        self._ffmpeg = ffmpeg_bin
        self._argv = None
        self._proc: Optional["asyncio.subprocess.Process"] = None

    @property
    def process(self) -> "asyncio.subprocess.Process":
        """Return a Popen object or None of not running."""
        return self._proc

    @property
    def is_running(self) -> bool:
        """Return True if ffmpeg is running."""
        if self._proc is None or self._proc.returncode is not None:
            return False
        return True

    def _generate_ffmpeg_cmd(
        self,
        cmd: List[str],
        input_source: Optional[str],
        output: Optional[str],
        extra_cmd: Optional[str] = None,
    ) -> None:
        """Generate ffmpeg command line."""
        self._argv = [self._ffmpeg]

        # start command init
        if input_source is not None:
            self._put_input(input_source)
        self._argv.extend(cmd)

        # exists a extra cmd from customer
        if extra_cmd is not None:
            self._argv.extend(shlex.split(extra_cmd))

        self._merge_filters()
        self._put_output(output)

    def _put_input(self, input_source: str) -> None:
        """Put input string to ffmpeg command."""
        input_cmd = shlex.split(str(input_source))
        if len(input_cmd) > 1:
            self._argv.extend(input_cmd)
        else:
            self._argv.extend(["-i", input_source])

    def _put_output(self, output: Optional[str]) -> None:
        """Put output string to ffmpeg command."""
        if output is None:
            self._argv.extend(["-f", "null", "-"])
            return

        output_cmd = shlex.split(str(output))
        if len(output_cmd) > 1:
            self._argv.extend(output_cmd)
        else:
            self._argv.append(output)

    def _merge_filters(self) -> None:
        """Merge all filter config in command line."""
        for opts in (["-filter:a", "-af"], ["-filter:v", "-vf"]):
            filter_list = []
            new_argv = []
            cmd_iter = iter(self._argv)
            for element in cmd_iter:
                if element in opts:
                    filter_list.insert(0, next(cmd_iter))
                else:
                    new_argv.append(element)

            # update argv if changes
            if filter_list:
                new_argv.extend([opts[0], ",".join(filter_list)])
                self._argv = new_argv.copy()

    def _clear(self) -> None:
        """Clear member variable after close."""
        self._argv = None
        self._proc = None

    async def open(
        self,
        cmd: List[str],
        input_source: Optional[str],
        output: Optional[str] = "-",
        extra_cmd: Optional[str] = None,
        stdout_pipe: bool = True,
        stderr_pipe: bool = False,
    ) -> bool:
        """Start a ffmpeg instance and pipe output."""
        stdout = asyncio.subprocess.PIPE if stdout_pipe else asyncio.subprocess.DEVNULL
        stderr = asyncio.subprocess.PIPE if stderr_pipe else asyncio.subprocess.DEVNULL

        if self.is_running:
            _LOGGER.warning("FFmpeg is already running!")
            return True

        # set command line
        self._generate_ffmpeg_cmd(cmd, input_source, output, extra_cmd)

        # start ffmpeg
        _LOGGER.debug("Start FFmpeg with %s", str(self._argv))
        try:
            self._proc = await asyncio.create_subprocess_exec(
                *self._argv,
                bufsize=0,
                stdin=asyncio.subprocess.PIPE,
                stdout=stdout,
                stderr=stderr,
                close_fds=False,
            )
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.exception("FFmpeg fails %s", err)
            self._clear()
            return False

        return self._proc is not None

    async def close(self, timeout=5) -> None:
        """Stop a ffmpeg instance."""
        if not self.is_running:
            _LOGGER.warning("FFmpeg isn't running!")
            return

        # Can't use communicate because we attach the output to a streamreader
        # send stop to ffmpeg
        try:
            self._proc.stdin.write(b"q")
            async with asyncio_timeout(timeout):
                await self._proc.wait()
            _LOGGER.debug("Close FFmpeg process")

        except (asyncio.TimeoutError, ValueError):
            _LOGGER.warning("Timeout while waiting of FFmpeg")
            self.kill()

        finally:
            self._clear()

    def kill(self) -> None:
        """Kill ffmpeg job."""
        self._proc.kill()
        background_task = asyncio.create_task(self._proc.communicate())
        _BACKGROUND_TASKS.add(background_task)
        background_task.add_done_callback(_BACKGROUND_TASKS.remove)

    async def get_reader(self, source=FFMPEG_STDOUT) -> asyncio.StreamReader:
        """Create and return streamreader."""
        if source == FFMPEG_STDOUT:
            return self._proc.stdout
        return self._proc.stderr


class HAFFmpegWorker(HAFFmpeg):
    """Read FFmpeg output to queue."""

    def __init__(self, ffmpeg_bin: str):
        """Init noise sensor."""
        super().__init__(ffmpeg_bin)

        self._queue = asyncio.Queue()
        self._input = None
        self._read_task = None

    async def close(self, timeout: int = 5) -> None:
        """Stop a ffmpeg instance.

        Return a coroutine
        """
        if self._read_task is not None and not self._read_task.cancelled():
            self._read_task.cancel()

        return await super().close(timeout)

    async def _process_lines(self, pattern: Optional[str] = None) -> None:
        """Read line from pipe they match with pattern."""
        if pattern is not None:
            cmp = re.compile(pattern)

        _LOGGER.debug("Start working with pattern '%s'.", pattern)

        # read lines
        while self.is_running:
            try:
                line = await self._input.readline()
                if not line:
                    break
                line = line.decode()
            except Exception:  # pylint: disable=broad-except
                break

            match = True if pattern is None else cmp.search(line)
            if match:
                _LOGGER.debug("Process: %s", line)
                await self._queue.put(line)

        try:
            await self._proc.wait()
        finally:
            await self._queue.put(None)
            _LOGGER.debug("Stopped reading ffmpeg output.")

    async def _worker_process(self) -> None:
        """Process output line."""
        raise NotImplementedError()

    async def start_worker(
        self,
        cmd: List[str],
        input_source: str,
        output: Optional[str] = None,
        extra_cmd: Optional[str] = None,
        pattern: Optional[str] = None,
        reading: str = FFMPEG_STDERR,
    ) -> None:
        """Start ffmpeg do process data from output."""
        if self.is_running:
            _LOGGER.warning("Can't start worker. It is allready running!")
            return

        if reading == FFMPEG_STDERR:
            stdout = False
            stderr = True
        else:
            stdout = True
            stderr = False

        # start ffmpeg and reading to queue
        await self.open(
            cmd=cmd,
            input_source=input_source,
            output=output,
            extra_cmd=extra_cmd,
            stdout_pipe=stdout,
            stderr_pipe=stderr,
        )

        self._input = await self.get_reader(reading)

        # start background processing
        self._read_task = self._loop.create_task(self._process_lines(pattern))
        self._loop.create_task(self._worker_process())
