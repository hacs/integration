"""HACS Startup constrains."""
# pylint: disable=bad-continuation
import os

from .const import CUSTOM_UPDATER_LOCATIONS, CUSTOM_UPDATER_WARNING
from .helpers.misc import version_left_higher_then_right

from custom_components.hacs.globals import get_hacs

MINIMUM_HA_VERSION = "0.110.0"


def check_constrains():
    """Check HACS constrains."""
    if not constrain_translations():
        return False
    if not constrain_custom_updater():
        return False
    if not constrain_version():
        return False
    return True


def constrain_custom_updater():
    """Check if custom_updater exist."""
    hacs = get_hacs()
    for location in CUSTOM_UPDATER_LOCATIONS:
        if os.path.exists(location.format(hacs.system.config_path)):
            msg = CUSTOM_UPDATER_WARNING.format(
                location.format(hacs.system.config_path)
            )
            hacs.logger.critical(msg)
            return False
    return True


def constrain_version():
    """Check if the version is valid."""
    hacs = get_hacs()
    if not version_left_higher_then_right(hacs.system.ha_version, MINIMUM_HA_VERSION):
        hacs.logger.critical(
            f"You need HA version {MINIMUM_HA_VERSION} or newer to use this integration."
        )
        return False
    return True


def constrain_translations():
    """Check if traslations exist."""
    hacs = get_hacs()
    if not os.path.exists(
        f"{hacs.system.config_path}/custom_components/hacs/translations"
    ):
        hacs.logger.critical("You are missing the translations directory.")
        return False
    return True
