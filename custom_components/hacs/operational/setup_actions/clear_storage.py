"""Starting setup task: clear storage."""
import os

from custom_components.hacs.share import get_hacs
from ...enums import HacsSetupTask


async def async_clear_storage():
    """Async wrapper for clear_storage"""
    hacs = get_hacs()
    hacs.log.info("Setup task %s", HacsSetupTask.CATEGORIES)
    await hacs.hass.async_add_executor_job(_clear_storage)


def _clear_storage():
    """Clear old files from storage."""
    hacs = get_hacs()
    storagefiles = ["hacs"]
    for s_f in storagefiles:
        path = f"{hacs.system.config_path}/.storage/{s_f}"
        if os.path.isfile(path):
            hacs.log.info(f"Cleaning up old storage file {path}")
            os.remove(path)
