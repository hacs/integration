"""Storage handers."""
# pylint: disable=import-outside-toplevel
from homeassistant.helpers.json import JSONEncoder

from custom_components.hacs.const import VERSION_STORAGE
from .logger import getLogger

_LOGGER = getLogger()


def get_store_for_key(hass, key):
    """Create a Store object for the key."""
    key = key if "/" in key else f"hacs.{key}"
    from homeassistant.helpers.storage import Store

    return Store(hass, VERSION_STORAGE, key, encoder=JSONEncoder)


async def async_load_from_store(hass, key):
    """Load the retained data from store and return de-serialized data."""
    store = get_store_for_key(hass, key)
    restored = await store.async_load()
    if restored is None:
        return {}
    return restored


async def async_save_to_store(hass, key, data):
    """Generate dynamic data to store and save it to the filesystem."""
    current = await async_load_from_store(hass, key)
    if current is None or current != data:
        await get_store_for_key(hass, key).async_save(data)
        return
    _LOGGER.debug(
        "Did not store data for '%s'. Content did not change",
        key if "/" in key else f"hacs.{key}",
    )


async def async_remove_store(hass, key):
    """Remove a store element that should no longer be used"""
    if "/" not in key:
        return
    await get_store_for_key(hass, key).async_remove()
