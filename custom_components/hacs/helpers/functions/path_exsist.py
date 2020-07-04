# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
import os

from custom_components.hacs.share import get_hacs


def path_exsist(path) -> bool:
    return os.path.exists(path)


async def async_path_exsist(path) -> bool:
    hass = get_hacs().hass
    return await hass.async_add_executor_job(path_exsist, path)
