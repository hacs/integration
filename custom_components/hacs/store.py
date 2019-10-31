"""Storage handers."""
from homeassistant.helpers.json import JSONEncoder
from homeassistant.helpers.storage import Store
from .hacsbase.const import STORAGE_VERSION


async def async_load_from_store(hass, key):
    """Load the retained data from store and return de-serialized data."""
    store = Store(hass, STORAGE_VERSION, f"hacs.{key}", encoder=JSONEncoder)
    restored = await store.async_load()
    if restored is None:
        return {}
    return restored


async def async_save_to_store(hass, key, data):
    """Generate dynamic data to store and save it to the filesystem."""
    store = Store(hass, STORAGE_VERSION, f"hacs.{key}", encoder=JSONEncoder)
    await store.async_save(data)
