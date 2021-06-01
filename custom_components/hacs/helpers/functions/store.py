"""Storage handers."""
# pylint: disable=import-outside-toplevel
from homeassistant.helpers.json import JSONEncoder

from homeassistant.helpers.storage import Store
from homeassistant.util import json as json_util

from custom_components.hacs.const import VERSION_STORAGE
from .logger import getLogger

_LOGGER = getLogger()


class HACSStore(Store):
    """A subclass of Store that allows multiple loads in the executor."""

    def load(self):
        """Load the data from disk if version matches."""
        data = json_util.load_json(self.path)
        if data == {} or data["version"] != self.version:
            return None
        return data["data"]


def get_store_key(key):
    """Return the key to use with homeassistant.helpers.storage.Storage."""
    return key if "/" in key else f"hacs.{key}"


def _get_store_for_key(hass, key, encoder):
    """Create a Store object for the key."""
    return HACSStore(hass, VERSION_STORAGE, get_store_key(key), encoder=encoder)


def get_store_for_key(hass, key):
    """Create a Store object for the key."""
    return _get_store_for_key(hass, key, JSONEncoder)


async def async_load_from_store(hass, key):
    """Load the retained data from store and return de-serialized data."""
    return await get_store_for_key(hass, key).async_load() or {}


async def async_save_to_store_default_encoder(hass, key, data):
    """Generate store json safe data to the filesystem.

    The data is expected to be encodable with the default
    python json encoder. It should have already been passed through
    JSONEncoder if needed.
    """
    await _get_store_for_key(hass, key, None).async_save(data)


async def async_save_to_store(hass, key, data):
    """Generate dynamic data to store and save it to the filesystem.

    The data is only written if the content on the disk has changed
    by reading the existing content and comparing it.

    If the data has changed this will generate two executor jobs

    If the data has not changed this will generate one executor job
    """
    current = await async_load_from_store(hass, key)
    if current is None or current != data:
        await get_store_for_key(hass, key).async_save(data)
        return
    _LOGGER.debug(
        "Did not store data for '%s'. Content did not change",
        get_store_key(key),
    )


async def async_remove_store(hass, key):
    """Remove a store element that should no longer be used."""
    if "/" not in key:
        return
    await get_store_for_key(hass, key).async_remove()
