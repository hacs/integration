from __future__ import annotations

__version__ = "1.4.2"

import asyncio
import importlib
import sys
from types import ModuleType

_MODULE_CACHE: dict[str, ModuleType] = {}


async def recover_adapter(hci: int, mac: str) -> bool:
    """Recover the Bluetooth adapter with the given HCI and MAC address.

    This function is a wrapper that late imports
    the `bluetooth_auto_recovery.recover` module and calls
    its `recover_adapter` function.
    """
    recover_module_name = f"{__package__}.recover"

    if not (recover_module := _MODULE_CACHE.get(recover_module_name)):
        loop = asyncio.get_running_loop()
        recover_module = await loop.run_in_executor(
            None, importlib.import_module, recover_module_name
        )
        _MODULE_CACHE[recover_module_name] = recover_module  # type: ignore
        this_module = sys.modules[__package__]
        this_module.recover_adapter = recover_module.recover_adapter  # type: ignore

    return await recover_module.recover_adapter(hci, mac)  # type: ignore


__all__ = ["recover_adapter"]
