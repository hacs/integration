"""The bluetooth utilities."""

from functools import cache
from pathlib import Path

from bluetooth_auto_recovery import recover_adapter


async def async_reset_adapter(adapter: str | None, mac_address: str) -> bool | None:
    """Reset the adapter."""
    if adapter and adapter.startswith("hci"):
        adapter_id = int(adapter[3:])
        return await recover_adapter(adapter_id, mac_address)
    return False


@cache
def is_docker_env() -> bool:
    """Return True if we run in a docker env."""
    return Path("/.dockerenv").exists()
