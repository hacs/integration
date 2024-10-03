"""Synology DownloadStation API wrapper."""

from __future__ import annotations

from synology_dsm.api import SynoBaseApi

from .task import SynoDownloadTask


class SynoDownloadStation(SynoBaseApi["dict[str, SynoDownloadTask]"]):
    """An implementation of a Synology DownloadStation."""

    API_KEY = "SYNO.DownloadStation.*"
    INFO_API_KEY = "SYNO.DownloadStation.Info"
    STAT_API_KEY = "SYNO.DownloadStation.Statistic"
    TASK_API_KEY = "SYNO.DownloadStation.Task"
    REQUEST_DATA = {
        "additional": "detail,file"
    }  # Can contain: detail, transfer, file, tracker, peer

    async def update(self) -> None:
        """Update tasks from API."""
        self._data = {}
        raw_data = await self._dsm.get(self.TASK_API_KEY, "List", self.REQUEST_DATA)
        if not isinstance(raw_data, dict) or (data := raw_data.get("data")) is None:
            return

        for task_data in data["tasks"]:
            if task_data["id"] in self._data:
                self._data[task_data["id"]].update(task_data)
            else:
                self._data[task_data["id"]] = SynoDownloadTask(task_data)

    # Global
    async def get_info(self) -> dict | None:
        """Return general informations about the Download Station instance."""
        raw_data = await self._dsm.get(self.INFO_API_KEY, "GetInfo")
        if isinstance(raw_data, dict):
            return raw_data
        return None

    async def get_config(self) -> dict | None:
        """Return configuration about the Download Station instance."""
        raw_data = await self._dsm.get(self.INFO_API_KEY, "GetConfig")
        if isinstance(raw_data, dict):
            return raw_data
        return None

    async def get_stat(self) -> dict | None:
        """Return statistic about the Download Station instance."""
        raw_data = await self._dsm.get(self.STAT_API_KEY, "GetInfo")
        if isinstance(raw_data, dict):
            return raw_data
        return None

    # Downloads
    def get_all_tasks(self) -> list[SynoDownloadTask]:
        """Return a list of tasks."""
        return list(self._data.values())

    def get_task(self, task_id: str) -> SynoDownloadTask | None:
        """Return task matching task_id."""
        return self._data.get(task_id)

    async def create(
        self,
        uri: str | list[str],
        unzip_password: str | None = None,
        destination: str | None = None,
    ) -> dict | None:
        """Create a new task (uri accepts HTTP/FTP/magnet/ED2K links)."""
        res = await self._dsm.post(
            self.TASK_API_KEY,
            "Create",
            {
                "uri": ",".join(uri) if isinstance(uri, list) else uri,
                "unzip_password": unzip_password,
                "destination": destination,
            },
        )
        await self.update()
        if isinstance(res, dict):
            return res
        return None

    async def pause(self, task_id: str | list[str]) -> dict | None:
        """Pause a download task."""
        res = await self._dsm.get(
            self.TASK_API_KEY,
            "Pause",
            {"id": ",".join(task_id) if isinstance(task_id, list) else task_id},
        )
        await self.update()
        if isinstance(res, dict):
            return res
        return None

    async def resume(self, task_id: str | list[str]) -> dict | None:
        """Resume a paused download task."""
        res = await self._dsm.get(
            self.TASK_API_KEY,
            "Resume",
            {"id": ",".join(task_id) if isinstance(task_id, list) else task_id},
        )
        await self.update()
        if isinstance(res, dict):
            return res
        return None

    async def delete(
        self, task_id: str | list[str], force_complete: bool = False
    ) -> dict | None:
        """Delete a download task."""
        res = await self._dsm.get(
            self.TASK_API_KEY,
            "Delete",
            {
                "id": ",".join(task_id) if isinstance(task_id, list) else task_id,
                "force_complete": force_complete,
            },
        )
        await self.update()
        if isinstance(res, dict):
            return res
        return None
