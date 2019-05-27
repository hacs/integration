"""Storage handler."""
# pylint: disable=broad-except
import logging
import json
from custom_components.hacs.const import STORENAME, VERSION, DATA_SCHEMA

_LOGGER = logging.getLogger('custom_components.hacs.storage')

async def load_storage_file(hass):
    """Load datafile from storage."""
    import aiofiles
    datastore = "{}/.storage/{}".format(hass.config.path(), STORENAME)
    _LOGGER.debug("Reading from datastore %s.", datastore)

    returndata = {}

    try:
        async with aiofiles.open(datastore, mode='r', encoding="utf-8", errors="ignore") as datafile:
            data = await datafile.read()
            returndata = json.loads(data)
            datafile.close()

    except Exception as error:
        msg = "Could not load data from {} - {}".format(datastore, error)
        _LOGGER.debug(msg)

    return returndata

async def data_migration(hass):
    """Run data migration."""
    import aiofiles

    _LOGGER.info("Running datamigration.")

    datastore = "{}/.storage/{}".format(hass.config.path(), STORENAME)
    data = None

    # Get current data:
    try:
        async with aiofiles.open(datastore, mode='r', encoding="utf-8", errors="ignore") as datafile:
            data = await datafile.read()
            data = json.loads(data)
            datafile.close()
    except Exception as error:
        _LOGGER.debug("Could not load data from %s - %s", datastore, error)

    if not data:
        data["repositories"] = {}
        data["custom"] = {"integration": [], "plugin": []}
        data["hacs"] = {"local": VERSION, "remote": None, "schema": DATA_SCHEMA}
        return

    data["repositories"] = {}
    data["custom"] = {}
    data["custom"]["integration"] = data["custom"].get("integration", [])
    data["custom"]["plugin"] = data["custom"].get("plugin", [])
    data["hacs"] = {}
    data["hacs"]['local'] = VERSION
    data["hacs"]['remote'] = data["hacs"].get("remote")
    data["hacs"]['schema'] = DATA_SCHEMA


    for element in data["repositories"]:
        elementdata = Element(data["repositories"][element]["element_type"], element)
        for entry in data["repositories"][element]:

            if entry == "something":
                # do something special here
                elementdata.__setattr__(entry, data["repositories"][element][entry])

            elif entry == "something_else":
                # do something special here
                elementdata.__setattr__(entry, data["repositories"][element][entry])

            else:
                # We can reuse it
                elementdata.__setattr__(entry, data["repositories"][element][entry])



        # Since this function is used during startup, we clear these flags
        elementdata.__setattr__("pending_restart", False)

        data["repositories"][element] = elementdata
