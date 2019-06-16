"""Log handler."""
# pylint: disable=broad-except
import logging
import aiofiles

from ..const import STARTUP

_LOGGER = logging.getLogger("custom_components.hacs.log")


async def get_log_file_content(config_dir):
    """Get logfile content."""
    log_file = "{}/home-assistant.log".format(config_dir)

    interesting = "<pre style='margin: 0'>{}</pre>".format(STARTUP)

    try:
        async with aiofiles.open(
            log_file, mode="r", encoding="utf-8", errors="ignore"
        ) as localfile:
            logfile = await localfile.readlines()
            localfile.close()
        for line in logfile:
            if "[custom_components.hacs" in line or "[homeassistant.core" in line:
                line = line.replace("(MainThread)", "")
                line = line.replace(" DEBUG ", "")
                line = line.replace(" INFO ", "")
                line = line.replace(" WARNING ", "")
                line = line.replace(" ERROR ", "")
                line = line.replace(" CRITICAL ", "")
                interesting += "<pre style='margin: 0; white-space: pre-wrap'>{}</pre>".format(
                    line
                )
    except Exception as exception:
        _LOGGER.error(exception)
    return interesting
