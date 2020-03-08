"""HACS Configuration Schemas."""
# pylint: disable=dangerous-default-value
import voluptuous as vol
from .const import LOCALE

# Configuration:
TOKEN = "token"
SIDEPANEL_TITLE = "sidepanel_title"
SIDEPANEL_ICON = "sidepanel_icon"
APPDAEMON = "appdaemon"
NETDAEMON = "netdaemon"
PYTHON_SCRIPT = "python_script"
THEME = "theme"

# Options:
COUNTRY = "country"
DEBUG = "debug"
RELEASE_LIMIT = "release_limit"
EXPERIMENTAL = "experimental"


def hacs_base_config_schema(config: dict = {}, config_flow: bool = False) -> dict:
    """Return a shcema configuration dict for HACS."""
    if not config:
        config = {
            TOKEN: "xxxxxxxxxxxxxxxxxxxxxxxxxxx",
            SIDEPANEL_ICON: "mdi:alpha-c-box",
            SIDEPANEL_TITLE: "HACS",
            APPDAEMON: False,
            NETDAEMON: False,
            PYTHON_SCRIPT: False,
            THEME: False,
        }
    if config_flow:
        return {
            vol.Required(TOKEN, default=config.get(TOKEN)): str,
            vol.Optional(SIDEPANEL_TITLE, default=config.get(SIDEPANEL_TITLE)): str,
            vol.Optional(SIDEPANEL_ICON, default=config.get(SIDEPANEL_ICON)): str,
            vol.Optional(APPDAEMON, default=config.get(APPDAEMON)): bool,
            vol.Optional(NETDAEMON, default=config.get(NETDAEMON)): bool,
        }
    return {
        vol.Required(TOKEN, default=config.get(TOKEN)): str,
        vol.Optional(SIDEPANEL_TITLE, default=config.get(SIDEPANEL_TITLE)): str,
        vol.Optional(SIDEPANEL_ICON, default=config.get(SIDEPANEL_ICON)): str,
        vol.Optional(APPDAEMON, default=config.get(APPDAEMON)): bool,
        vol.Optional(NETDAEMON, default=config.get(NETDAEMON)): bool,
        vol.Optional(PYTHON_SCRIPT, default=config.get(PYTHON_SCRIPT)): bool,
        vol.Optional(THEME, default=config.get(THEME)): bool,
    }


def hacs_config_option_schema(options: dict = {}) -> dict:
    """Return a shcema for HACS configuration options."""
    if not options:
        options = {COUNTRY: "ALL", DEBUG: False, RELEASE_LIMIT: 5, EXPERIMENTAL: False}
    return {
        vol.Optional(COUNTRY, default=options.get(COUNTRY)): vol.In(LOCALE),
        vol.Optional(RELEASE_LIMIT, default=options.get(RELEASE_LIMIT)): int,
        vol.Optional(EXPERIMENTAL, default=options.get(EXPERIMENTAL)): bool,
        vol.Optional(DEBUG, default=options.get(DEBUG)): bool,
    }


def hacs_config_combined() -> dict:
    """Combine the configuration options."""
    base = hacs_base_config_schema()
    options = hacs_config_option_schema()

    for option in options:
        base[option] = options[option]

    return base
