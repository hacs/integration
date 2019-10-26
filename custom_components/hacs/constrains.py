"""HACS Startup constrains."""
# pylint: disable=bad-continuation
import os
import json
from distutils.version import LooseVersion

from .const import CUSTOM_UPDATER_LOCATIONS, CUSTOM_UPDATER_WARNING


def check_constans(hacs):
    """Check HACS constrains."""
    if not constrain_custom_updater(hacs):
        return False
    if not constrain_version(hacs):
        return False
    return True


def constrain_custom_updater(hacs):
    """Check if custom_updater exist."""
    for location in CUSTOM_UPDATER_LOCATIONS:
        if os.path.exists(location.format(hacs.system.config_path)):
            msg = CUSTOM_UPDATER_WARNING.format(
                location.format(hacs.system.config_path)
            )
            hacs.logger.critical(msg)
            return False
    return True


def constrain_version(hacs):
    """Check if the version is valid."""
    with open(
        f"{hacs.system.config_path}/custom_components/hacs/manifest.json", "r"
    ) as read:
        manifest = json.loads(read.read())

    # Check if HA is the required version.
    if LooseVersion(hacs.system.ha_version) < LooseVersion(manifest["homeassistant"]):
        hacs.logger.critical(
            f"You need HA version {manifest['homeassistant']} or newer to use this integration."
        )
        return False
    return True
