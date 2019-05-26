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

async def get_data_from_store(hass):
    """
    Get data from datastore.
    Returns a dict with information from the storage.
    example output: {"repositories": {}, "custom": {}, "hacs": {}}
    """
    import aiofiles
    from custom_components.hacs.blueprints import HacsRepositoryIntegration, HacsRepositoryPlugin
    datastore = "{}/.storage/{}".format(hass.config.path(), STORENAME)
    _LOGGER.debug("Reading from datastore %s.", datastore)

    repositories = {}
    returndata = {}

    try:
        async with aiofiles.open(datastore, mode='r', encoding="utf-8", errors="ignore") as datafile:
            data = await datafile.read()
            data = json.loads(data)
            datafile.close()

        returndata["custom"] = {}
        returndata["custom"]["integration"] = data["custom"].get("integration", [])
        returndata["custom"]["plugin"] = data["custom"].get("plugin", [])
        returndata["hacs"] = data["hacs"]

        for element in data["repositories"]:
            if data["repositories"][element]["repository_type"] == "integration":
                elementdata = HacsRepositoryIntegration(data["repositories"][element]["repository_name"])
            elif data["repositories"][element]["repository_type"] == "plugin":
                elementdata = HacsRepositoryPlugin(data["repositories"][element]["repository_name"])
            for entry in data["repositories"][element]:
                elementdata.__setattr__(entry, data["repositories"][element][entry])

            repositories[element] = elementdata

        returndata["repositories"] = repositories

    except Exception as error:
        msg = "Could not load data from {} - {}".format(datastore, error)
        _LOGGER.debug(msg)

    return repositories, returndata


async def write_to_data_store(hacs):
    """
    Write data to datastore.
    """
    import aiofiles
    datastore = "{}/.storage/{}".format(hacs.config_dir, STORENAME)
    _LOGGER.debug("Writing to datastore %s.", datastore)

    outdata = {}
    outdata["hacs"] = hacs.data["hacs"]
    outdata["custom"] = hacs.data["custom"]

    outdata["repositories"] = {}

    skip_keys = [
        "content_objects",
        "last_release_object",
        "pending_restart", # Reset on restart.
        "repository",
        "track",  # Reset on restart.
        "reasons",  # Reset on restart.
    ]

    for repository in hacs.repositories:
        elementdata = {}
        repository = hacs.repositories[repository]
        attributes = vars(repository)
        for key in attributes:
            if key not in skip_keys:
                elementdata[key] = attributes[key]

        outdata["repositories"][attributes["repository_id"]] = elementdata

    try:
        async with aiofiles.open(datastore, mode='w', encoding="utf-8", errors="ignore") as outfile:
            await outfile.write(json.dumps(outdata, indent=4))
            outfile.close()

    except Exception as error:
        msg = "Could not write data to {} - {}".format(datastore, error)
        _LOGGER.debug(msg)

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
