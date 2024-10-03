"""Synology API models."""

from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from synology_dsm import SynologyDSM


_DataT = TypeVar("_DataT")


class SynoBaseApi(Generic[_DataT]):
    """Base api class."""

    def __init__(self, dsm: "SynologyDSM") -> None:
        """Constructor method."""
        self._dsm = dsm
        self._data: _DataT = {}  # type: ignore[assignment]
