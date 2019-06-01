"""Download."""
import logging
import aiofiles

import async_timeout

from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger('custom_components.hacs.download')


async def async_download_file(hass, url):
    """
    Download files, and return the content.
    """
    if url is None:
        return

    # There is a bug somewhere... TODO: Find that bug....
    if "tags/" in url:
        url = url.replace("tags/", "")

    _LOGGER.debug("Donwloading %s", url)

    result = None

    try:
        with async_timeout.timeout(5, loop=hass.loop):
            request = await async_get_clientsession(hass).get(url)

            # Make sure that we got a valid result
            if request.status == 200:
                result = await request.text()
            else:
                _LOGGER.debug(
                    "Got status code %s when trying to download %s", request.status, url
                )

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.debug("Downloading %s failed with %s", url, error)

    return result


async def async_save_file(location, content):
    """Save files."""
    if "-bundle" in location:
        location = location.replace("-bundle", "")

    _LOGGER.debug("Saving %s", location)

    try:
        async with aiofiles.open(location, mode='w', encoding="utf-8", errors="ignore") as outfile:
            await outfile.write(content)
            outfile.close()

    except Exception as error:  # pylint: disable=broad-except
        msg = "Could not write data to {} - {}".format(location, error)
        _LOGGER.debug(msg)
