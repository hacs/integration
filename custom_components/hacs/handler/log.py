"""Log handler."""
# pylint: disable=broad-except
import aiofiles

from custom_components.hacs.const import STARTUP

async def get_log_file_content(hass):
    """Get logfile content."""
    log_file = "{}/home-assistant.log".format(hass.config.path())

    interesting = "<pre style='margin: 0'>{}</pre>".format(STARTUP)

    try:
        async with aiofiles.open(
            log_file, mode='r', encoding="utf-8", errors="ignore") as localfile:
            logfile = await localfile.read()
            localfile.close()
        for line in logfile.readlines():
            if "[custom_components.hacs" in line:
                line = line.replace("(MainThread)", "")
                interesting += "<pre style='margin: 0'>{}</pre>".format(line)
    except Exception:
        pass
    return interesting
