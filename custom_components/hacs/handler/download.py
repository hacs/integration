"""Download."""
import os
import gzip
import shutil

import aiofiles
import async_timeout
from integrationhelper import Logger
import backoff
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from ..hacsbase.exceptions import HacsException


@backoff.on_exception(backoff.expo, Exception, max_tries=5)
async def async_download_file(hass, url):
    """
    Download files, and return the content.
    """
    logger = Logger("hacs.download.downloader")
    if url is None:
        return

    # There is a bug somewhere... TODO: Find that bug....
    if "tags/" in url:
        url = url.replace("tags/", "")

    logger.debug(f"Downloading {url}")

    result = None

    with async_timeout.timeout(60, loop=hass.loop):
        request = await async_get_clientsession(hass).get(url)

        # Make sure that we got a valid result
        if request.status == 200:
            result = await request.read()
        else:
            raise HacsException(
                "Got status code {} when trying to download {}".format(
                    request.status, url
                )
            )

    return result


async def async_save_file(location, content):
    """Save files."""
    logger = Logger("hacs.download.save")
    logger.debug(f"Saving {location}")
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

        # Create gz for .js files
        if os.path.isfile(location):
            if location.endswith(".js") or location.endswith(".css"):
                with open(location, "rb") as f_in:
                    with gzip.open(location + ".gz", "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)

    except Exception as error:  # pylint: disable=broad-except
        msg = "Could not write data to {} - {}".format(location, error)
        logger.error(msg)
        return False

    return os.path.exists(location)
