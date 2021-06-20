"""Download."""
import gzip
import os
import shutil

from ...share import get_hacs


async def async_save_file(location, content):
    """Save files."""
    hacs = get_hacs()
    hacs.log.debug("Saving %s", location)
    mode = "w"
    encoding = "utf-8"
    errors = "ignore"

    if not isinstance(content, str):
        mode = "wb"
        encoding = None
        errors = None

    def write_file():
        """Wrapper to write file."""
        with open(location, mode=mode, encoding=encoding, errors=errors) as outfile:
            outfile.write(content)

    try:
        await hacs.hass.async_add_executor_job(write_file)

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
                hacs.log.info("Removing old theme file %s", combined)
                os.remove(combined)

    except (Exception, BaseException) as error:  # pylint: disable=broad-except
        hacs.log.error("Could not write data to %s - %s", location, error)
        return False

    return os.path.exists(location)
