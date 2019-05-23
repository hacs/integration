"""Storage handler."""
import logging
import json
from custom_components.hacs.const import STORENAME
from custom_components.hacs.element import Element

_LOGGER = logging.getLogger(__name__)


async def get_data_from_store(hass, github):
    """
    Get data from datastore.
    Returns a dict with information from the storage.
    example output: {"elements": {}, "repos": {}, "hacs": {}}
    """
    datastore = "{}/.storage/{}".format(hass.config.path(), STORENAME)
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
            elementdata = Element(hass, github, data["elements"][element]["element_type"], element)
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
        elementdata['remote_dir_location'] = output["elements"][element].remote_dir_location
        elementdata['repo'] = output["elements"][element].repo
        elementdata['github_ref'] = output["elements"][element].github_ref
        elementdata['github_element_content_files'] = output["elements"][element].github_element_content_files
        elementdata['github_element_content_path'] = output["elements"][element].github_element_content_path
        elementdata['pending_restart'] = output["elements"][element].pending_restart
        elementdata['pending_update'] = output["elements"][element].pending_update
        elementdata['trackable'] = output["elements"][element].trackable
        elementdata['hidden'] = output["elements"][element].hidden

        outdata["elements"][output["elements"][element].element_id] = elementdata

    try:
        with open(datastore, "w", encoding="utf-8", errors="ignore") as outfile:
            json.dump(outdata, outfile, indent=4)
            outfile.close()

    except Exception as error:  # pylint: disable=broad-except
        msg = "Could not write data to {} - {}".format(datastore, error)
        _LOGGER.debug(msg)
