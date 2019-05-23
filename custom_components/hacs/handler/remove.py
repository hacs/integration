"""Remove elements."""
import logging
import shutil
import os
import asyncio

from custom_components.hacs.const import DOMAIN_DATA
from custom_components.hacs.handler.storage import write_to_data_store
from custom_components.hacs.handler.update import update_data_after_action

_LOGGER = logging.getLogger(__name__)


async def remove_element(hass, element):
    """Remove an element."""
    _LOGGER.debug("Staring removal of %s", element.element_id)

    ha_base_dir = hass.config.path()

    if element.element_type == "integration":
        elementdir = "{}/custom_components/{}".format(ha_base_dir, element.element_id)

    elif element.element_type == "plugin":
        elementdir = "{}/www/community/{}".format(ha_base_dir, element.element_id)

    if os.path.exists(elementdir):
        shutil.rmtree(elementdir)

        while os.path.exists(elementdir):
            _LOGGER.debug("%s still exist, waiting 1s and checking again.", elementdir)
            await asyncio.sleep(1)

    if element.repo.split("/")[0] not in ["custom-cards", "custom-components"]:
        if element.repo not in hass.data[DOMAIN_DATA]["repos"][element.element_type]:
            _LOGGER.debug("Repo no longer in reistry, removing from store.")
            del hass.data[DOMAIN_DATA]["elements"][element.element_id]
            await write_to_data_store(hass.config.path(), hass.data[DOMAIN_DATA])
            return
        else:
            _LOGGER.debug("Repo in reistry, keeping in store.")

    # Update hass.data
    element.installed_version = None
    element.isinstalled = False
    element.restart_pending = True
    await update_data_after_action(hass, element)

async def remove_repo(hass, repo):
    """Remove a repo."""
    # TODO: Fail HARD if installed, and give back a message about that.
    _LOGGER.debug("Staring removal of %s", repo)
    element = None
    if repo.split("/")[-1] in hass.data[DOMAIN_DATA]["elements"]:
        element = hass.data[DOMAIN_DATA]["elements"][repo.split("/")[-1]]

    if element is not None:
        hass.data[DOMAIN_DATA]["repos"][element.element_type].remove(repo)
        if not element.isinstalled:
            await remove_element(hass, element)
        else:
            _LOGGER.debug("Element is installed keeping in store.")
    else:
        if repo in hass.data[DOMAIN_DATA]["repos"]["plugin"]:
            hass.data[DOMAIN_DATA]["repos"]["plugin"].remove(repo)
        elif repo in hass.data[DOMAIN_DATA]["repos"]["integration"]:
            hass.data[DOMAIN_DATA]["repos"]["integration"].remove(repo)
