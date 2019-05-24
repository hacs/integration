"""Storage handler."""
import logging
import json
from custom_components.hacs.const import STORENAME, DOMAIN_DATA, VERSION, DATA_SCHEMA
from custom_components.hacs.element import Element

_LOGGER = logging.getLogger(__name__)

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

    for element in output["elements"]:
        elementdata = {}

        elementdata['authors'] = output["elements"][element].authors
        elementdata['avaiable_version'] = output["elements"][element].avaiable_version
        elementdata['description'] = output["elements"][element].description
        elementdata['element_id'] = output["elements"][element].element_id
        elementdata['element_type'] = output["elements"][element].element_type
        elementdata['info'] = output["elements"][element].info
        elementdata['installed_version'] = output["elements"][element].installed_version
        elementdata['isinstalled'] = output["elements"][element].isinstalled
        elementdata['github_last_update'] = output["elements"][element].github_last_update
        elementdata['manifest'] = output["elements"][element].manifest
        elementdata['name'] = output["elements"][element].name
        elementdata['releases'] = output["elements"][element].releases
        elementdata['jstype'] = output["elements"][element].jstype
        elementdata['remote_dir_location'] = output["elements"][element].remote_dir_location
        elementdata['repo'] = output["elements"][element].repo
        elementdata['github_ref'] = output["elements"][element].github_ref
        elementdata['github_element_content_files'] = output["elements"][element].github_element_content_files
        elementdata['github_element_content_path'] = output["elements"][element].github_element_content_path
        elementdata['pending_restart'] = output["elements"][element].pending_restart
        elementdata['pending_update'] = output["elements"][element].pending_update
        elementdata['trackable'] = output["elements"][element].trackable
        elementdata['reason'] = output["elements"][element].reason
        elementdata['hidden'] = output["elements"][element].hidden

        outdata["elements"][output["elements"][element].element_id] = elementdata

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
        elementdata = Element(hass, github, data["elements"][element]["element_type"], element)
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
