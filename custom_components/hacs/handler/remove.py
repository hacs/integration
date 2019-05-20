"""Remove elements."""
import logging
import shutil
import os
import asyncio
from custom_components.hacs.const import DOMAIN_DATA

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

    # Update hass.data
    del hass.data[DOMAIN_DATA]["elements"][element.element_id]
