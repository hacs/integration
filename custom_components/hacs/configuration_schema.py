"""HACS Configuration Schemas."""
# pylint: disable=dangerous-default-value
import voluptuous as vol
from .const import LOCALE

# Configuration:
TOKEN = "token"
SIDEPANEL_TITLE = "sidepanel_title"
SIDEPANEL_ICON = "sidepanel_icon"
APPDAEMON = "appdaemon"
PYTHON_SCRIPT = "python_script"
THEME = "theme"

# Options:
COUNTRY = "country"
DEBUG = "debug"
RELEASE_LIMIT = "release_limit"
EXPERIMENTAL = "experimental"


def hacs_base_config_schema(config: dict = {}) -> dict:
    """Return a shcema configuration dict for HACS."""
    if not config:
        config = {
            TOKEN: "xxxxxxxxxxxxxxxxxxxxxxxxxxx",
            SIDEPANEL_TITLE: "Community",
            SIDEPANEL_ICON: "mdi:alpha-c-box",
            APPDAEMON: False,
            PYTHON_SCRIPT: False,
            THEME: False,
        }
    return {
        vol.Required(TOKEN, default=config.get(TOKEN)): str,
        vol.Optional(SIDEPANEL_TITLE, default=config.get(SIDEPANEL_TITLE)): str,
        vol.Optional(SIDEPANEL_ICON, default=config.get(SIDEPANEL_ICON)): str,
        vol.Optional(APPDAEMON, default=config.get(APPDAEMON)): bool,
        vol.Optional(PYTHON_SCRIPT, default=config.get(PYTHON_SCRIPT)): bool,
        vol.Optional(THEME, default=config.get(THEME)): bool,
    }


def hacs_config_option_schema(options: dict = {}) -> dict:
    """Return a shcema for HACS configuration options."""
    if not options:
        options = {COUNTRY: "ALL", DEBUG: False, RELEASE_LIMIT: 5, EXPERIMENTAL: False}
    return {
        vol.Optional("country", default=options.get(COUNTRY)): vol.In(LOCALE),
        vol.Optional(DEBUG, default=options.get(DEBUG)): bool,
        vol.Optional(RELEASE_LIMIT, default=options.get(RELEASE_LIMIT)): int,
        vol.Optional(EXPERIMENTAL, default=options.get(EXPERIMENTAL)): bool,
    }
