from __future__ import annotations

import platform

from ..adapters import BluetoothAdapters


def get_adapters() -> BluetoothAdapters:
    """Get the adapters."""
    if platform.system() == "Windows":
        from .windows import WindowsAdapters

        return WindowsAdapters()
    if platform.system() == "Darwin":
        from .macos import MacOSAdapters

        return MacOSAdapters()
    from .linux import LinuxAdapters

    return LinuxAdapters()
