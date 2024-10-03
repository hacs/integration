"""Base class for Bluetooth adapters."""

from __future__ import annotations

from abc import abstractproperty

from .history import AdvertisementHistory
from .models import AdapterDetails


class BluetoothAdapters:
    """Class for getting the bluetooth adapters on a system."""

    async def refresh(self) -> None:
        """Refresh the adapters."""

    @property
    def history(self) -> dict[str, AdvertisementHistory]:
        """Get the history."""
        return {}

    @abstractproperty
    @property
    def adapters(self) -> dict[str, AdapterDetails]:
        """Get the adapter details."""

    @abstractproperty
    @property
    def default_adapter(self) -> str:
        """Get the default adapter."""
