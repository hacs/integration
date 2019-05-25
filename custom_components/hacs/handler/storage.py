"""Storage handler."""
import logging
import json
from custom_components.hacs.const import STORENAME, DOMAIN_DATA, VERSION, DATA_SCHEMA
from custom_components.hacs.element import Element

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

    except Exception as error:  # pylint: disable=broad-except
        msg = "Could not load data from {} - {}".format(datastore, error)
        _LOGGER.debug(msg)

    return returndata

async def get_data_from_store(hass, github):
    """
    Get data from datastore.
    Returns a dict with information from the storage.
    example output: {"elements": {}, "repos": {}, "hacs": {}}
    """
    import aiofiles
    datastore = "{}/.storage/{}".format(hass.config.path(), STORENAME)
    _LOGGER.debug("Reading from datastore %s.", datastore)

    elements = {}
    returndata = {}

    try:
        async with aiofiles.open(datastore, mode='r', encoding="utf-8", errors="ignore") as datafile:
            data = await datafile.read()
            data = json.loads(data)
            datafile.close()

        returndata["repos"] = {}
        returndata["repos"]["integration"] = data["repos"].get("integration", [])
        returndata["repos"]["plugin"] = data["repos"].get("plugin", [])
        returndata["hacs"] = data["hacs"]

        for element in data["elements"]:
            elementdata = Element(data["elements"][element]["element_type"], element)
            for entry in data["elements"][element]:
                elementdata.__setattr__(entry, data["elements"][element][entry])

            # Since this function is used during startup, we clear these flags
            elementdata.__setattr__("restart_pending", False)

            elements[element] = elementdata

        returndata["elements"] = elements

    except Exception as error:  # pylint: disable=broad-except
        msg = "Could not load data from {} - {}".format(datastore, error)
        _LOGGER.debug(msg)

    return returndata


async def write_to_data_store(basedir, output):
    """
    Write data to datastore.
    """
    import aiofiles
    datastore = "{}/.storage/{}".format(basedir, STORENAME)
    _LOGGER.debug("Writing to datastore %s.", datastore)

    outdata = {}
    outdata["hacs"] = output["hacs"]
    outdata["repos"] = output["repos"]

    # 'elements' contains Class objects and cans be stored directly, so we extract the important part.
    outdata["elements"] = {}

    skip_keys = [
        "content_objects",
        "last_release_object",
        "pending_restart",
        "repository"
    ]

    for element in output["elements"]:
        elementdata = {}
        element = output["elements"][element]
        attributes = vars(element)
        for key in attributes:
            if key not in skip_keys:
                elementdata[key] = attributes[key]

        outdata["elements"][attributes["repository_id"]] = elementdata

    try:
        async with aiofiles.open(datastore, mode='w', encoding="utf-8", errors="ignore") as outfile:
            await outfile.write(json.dumps(outdata, indent=4))
            outfile.close()

    except Exception as error:  # pylint: disable=broad-except
        msg = "Could not write data to {} - {}".format(datastore, error)
        _LOGGER.debug(msg)

async def data_migration(hass, github):
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
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.debug("Could not load data from %s - %s", datastore, error)

    if not data:
        data["elements"] = {}
        data["repos"] = {"integration": [], "plugin": []}
        data["hacs"] = {"local": VERSION, "remote": None, "schema": DATA_SCHEMA}
        return

    data["elements"] = {}
    data["repos"] = {}
    data["repos"]["integration"] = data["repos"].get("integration", [])
    data["repos"]["plugin"] = data["repos"].get("plugin", [])
    data["hacs"] = {}
    data["hacs"]['local'] = VERSION
    data["hacs"]['remote'] = data["hacs"].get("remote")
    data["hacs"]['schema'] = DATA_SCHEMA


    for element in data["elements"]:
        elementdata = Element(data["elements"][element]["element_type"], element)
        for entry in data["elements"][element]:

            if entry == "something":
                # do something special here
                elementdata.__setattr__(entry, data["elements"][element][entry])

            elif entry == "something_else":
                # do something special here
                elementdata.__setattr__(entry, data["elements"][element][entry])

            else:
                # We can reuse it
                elementdata.__setattr__(entry, data["elements"][element][entry])



        # Since this function is used during startup, we clear these flags
        elementdata.__setattr__("restart_pending", False)

        data["elements"][element] = elementdata
