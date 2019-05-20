"""Storage handler."""
import logging
import json
from custom_components.hacs.const import STORENAME
from custom_components.hacs.element import Element

_LOGGER = logging.getLogger(__name__)


async def get_data_from_store(basedir):
    """
    Get data from datastore.
    Returns a dict with information from the storage.
    example output: {"elements": {}, "repos": {}, "hacs": {}}
    """
    datastore = "{}/.storage/{}".format(basedir, STORENAME)
    _LOGGER.debug("Reading from datastore %s.", datastore)

    elements = {}
    returndata = {}

    try:
        with open(datastore, encoding="utf-8", errors="ignore") as localfile:
            data = json.load(localfile)
            localfile.close()

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
    datastore = "{}/.storage/{}".format(basedir, STORENAME)
    _LOGGER.debug("Writing to datastore %s.", datastore)

    outdata = {}
    outdata["hacs"] = output["hacs"]
    outdata["repos"] = output["repos"]

    # 'elements' contains Class objects and cans be stored directly, so we extract the important part.
    outdata["elements"] = {}

    for element in output["elements"]:
        elementdata = {}

        for attribute, value in output["elements"][element].__dict__.items():
            elementdata[attribute] = value

        outdata["elements"][output["elements"][element].element_id] = elementdata

    try:
        with open(datastore, "w", encoding="utf-8", errors="ignore") as outfile:
            json.dump(outdata, outfile, indent=4)
            outfile.close()

    except Exception as error:  # pylint: disable=broad-except
        msg = "Could not write data to {} - {}".format(datastore, error)
        _LOGGER.debug(msg)
