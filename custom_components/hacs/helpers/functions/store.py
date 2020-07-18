"""Storage handers."""
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store

from custom_components.hacs.const import VERSION_STORAGE


async def async_load_from_store(hass, key):
    """Load the retained data from store and return de-serialized data."""
    key = key if "/" in key else f"hacs.{key}"
    store = Store(hass, VERSION_STORAGE, key, encoder=JSONEncoder)
    restored = await store.async_load()
    if restored is None:
        return {}
    return restored


async def async_save_to_store(hass, key, data):
    """Generate dynamic data to store and save it to the filesystem."""
    key = key if "/" in key else f"hacs.{key}"
    store = Store(hass, VERSION_STORAGE, key, encoder=JSONEncoder)
    await store.async_save(data)


async def async_remove_store(hass, key):
    """Remove a store element that should no longer be used"""
    if "/" not in key:
        return
    store = Store(hass, VERSION_STORAGE, key, encoder=JSONEncoder)
    await store.async_remove()
