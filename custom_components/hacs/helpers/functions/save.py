"""Download."""
import gzip
import os
import shutil

import aiofiles

from custom_components.hacs.helpers.functions.logger import getLogger

_LOGGER = getLogger()


async def async_save_file(location, content):
    """Save files."""
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

        # Create gz for .js files
        if os.path.isfile(location):
            if location.endswith(".js") or location.endswith(".css"):
                with open(location, "rb") as f_in:
                    with gzip.open(location + ".gz", "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)

        # Remove with 2.0
        if "themes" in location and location.endswith(".yaml"):
            filename = location.split("/")[-1]
            base = location.split("/themes/")[0]
            combined = f"{base}/themes/{filename}"
            if os.path.exists(combined):
                _LOGGER.info("Removing old theme file %s", combined)
                os.remove(combined)

    except (Exception, BaseException) as error:  # pylint: disable=broad-except
        _LOGGER.error("Could not write data to %s - %s", location, error)
        return False

    return os.path.exists(location)
