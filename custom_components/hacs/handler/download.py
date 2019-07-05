"""Download."""
import gzip
import logging
import shutil

import aiofiles
import async_timeout

import backoff
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from ..hacsbase.exceptions import HacsNotSoBasicException

_LOGGER = logging.getLogger("custom_components.hacs.download")


@backoff.on_exception(backoff.expo, Exception, max_tries=5)
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

    with async_timeout.timeout(5, loop=hass.loop):
        request = await async_get_clientsession(hass).get(url)

        # Make sure that we got a valid result
        if request.status == 200:
            result = await request.read()
        else:
            raise HacsNotSoBasicException(
                "Got status code {} when trying to download {}".format(
                    request.status, url
                )
            )

    return result


async def async_save_file(location, content):
    """Save files."""
    if "-bundle" in location:
        location = location.replace("-bundle", "")
    if "lovelace-" in location.split("/")[-1]:
        search = location.split("/")[-1]
        replace = search.replace("lovelace-", "")
        location = location.replace(search, replace)

    _LOGGER.debug("Saving %s", location)
    mode = "w"
    encoding = "utf-8"
    errors = "ignore"

    if not isinstance(content, str):
        mode = "wb"
        encoding = None
        errors = None

    try:
        async with aiofiles.open(
            location, mode=mode, encoding=encoding, errors=errors
        ) as outfile:
            await outfile.write(content)
            outfile.close()

    except Exception as error:  # pylint: disable=broad-except
        msg = "Could not write data to {} - {}".format(location, error)
        _LOGGER.debug(msg)

    # Create gz for .js files
    if location.endswith(".js") or location.endswith(".css"):
        with open(location, "rb") as f_in:
            with gzip.open(location + ".gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
