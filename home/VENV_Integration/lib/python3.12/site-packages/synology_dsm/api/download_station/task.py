"""DownloadStation task."""

from __future__ import annotations

from typing import TypedDict

SynoDownloadTaskType = TypedDict(
    "SynoDownloadTaskType",
    {
        "additional": dict,
        "id": str,
        "size": int,
        "status": str,
        "title": str,
        "type": str,
        "username": str,
        "status_extra": dict,
    },
    total=False,
)


class SynoDownloadTask:
    """An representation of a Synology DownloadStation task."""

    def __init__(self, data: SynoDownloadTaskType):
        """Initialize a Download Station task."""
        self._data: SynoDownloadTaskType = data

    def update(self, data: SynoDownloadTaskType) -> None:
        """Update the task."""
        self._data = data

    @property
    def id(self) -> str:
        """Return id of the task."""
        return self._data["id"]

    @property
    def title(self) -> str:
        """Return title of the task."""
        return self._data["title"]

    @property
    def type(self) -> str:
        """Return type of the task (bt, nzb, http(s), ftp, emule)."""
        return self._data["type"]

    @property
    def username(self) -> str:
        """Return username of the task."""
        return self._data["username"]

    @property
    def size(self) -> int:
        """Return size of the task."""
        return self._data["size"]

    @property
    def status(self) -> str:
        """Return status of the task.

        Possible values: waiting, downloading, paused, finishing, finished,
            hash_checking, seeding, filehosting_waiting, extracting, error
        """
        return self._data["status"]

    @property
    def status_extra(self) -> dict | None:
        """Return status_extra of the task."""
        return self._data.get("status_extra")

    @property
    def additional(self) -> dict:
        """Return additional data of the task."""
        return self._data["additional"]
