from __future__ import annotations

__version__ = "0.1.6"

import asyncio
import pathlib

_OUI_DATA_FILE = pathlib.Path(__file__).parent.joinpath("oui.data")


class OUIManager:
    """Manages the OUI data."""

    def __init__(self) -> None:
        """Initialize the OUIManager."""
        self._oui_to_vendor: dict[str, str] = {}
        self._load_future: asyncio.Future[None] | None = None

    def get_vendor(self, mac: str) -> str | None:
        """Get the vendor for a MAC address."""
        if not self._oui_to_vendor:
            raise RuntimeError("OUI data not loaded, call async_load first")
        return self._oui_to_vendor.get(mac.replace(":", "")[:6].upper())

    async def async_load(self) -> None:
        """Load the OUI data."""
        if self._oui_to_vendor:
            return
        if self._load_future:
            await self._load_future
            return
        loop = asyncio.get_running_loop()
        self._load_future = loop.create_future()
        try:
            self._oui_to_vendor = await loop.run_in_executor(None, self._load_oui_data)
        except Exception as err:
            self._load_future.set_exception(err)
            raise
        else:
            self._load_future.set_result(None)
        finally:
            self._load_future = None

    def _load_oui_data(self) -> dict[str, str]:
        """Load the OUI data."""
        with open(_OUI_DATA_FILE) as f:
            oui_to_vendor: dict[str, str] = {}
            for line in f.read().splitlines():
                oui, _, vendor = line.partition("=")
                oui_to_vendor[oui] = vendor

        return oui_to_vendor


_OUI_MANAGER = OUIManager()


def is_loaded() -> bool:
    """Return if the OUI data is loaded."""
    return bool(_OUI_MANAGER._oui_to_vendor)


def get_vendor(mac: str) -> str | None:
    """Get the vendor for a MAC address."""
    return _OUI_MANAGER.get_vendor(mac)


async def async_load() -> None:
    """Load the OUI data."""
    await _OUI_MANAGER.async_load()


__all__ = ["async_load", "get_vendor", "is_loaded"]
