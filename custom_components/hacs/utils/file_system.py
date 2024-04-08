"""File system functions."""

from __future__ import annotations

import os
from typing import TypeAlias

from homeassistant.core import HomeAssistant

# From typeshed
StrOrBytesPath: TypeAlias = str | bytes | os.PathLike[str] | os.PathLike[bytes]
FileDescriptorOrPath: TypeAlias = int | StrOrBytesPath


async def async_exists(hass: HomeAssistant, path: FileDescriptorOrPath) -> bool:
    """Test whether a path exists."""
    return await hass.async_add_executor_job(os.path.exists, path)


async def async_remove(
    hass: HomeAssistant, path: StrOrBytesPath, *, dir_fd: int | None = None
) -> None:
    """Remove a path."""
    return await hass.async_add_executor_job(os.remove, path)
