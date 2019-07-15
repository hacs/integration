"""Constants for HACS"""
VERSION = "0.12.1"
NAME_LONG = "HACS (Home Assistant Community Store)"
NAME_SHORT = "HACS"
DOMAIN = "hacs"
PROJECT_URL = "https://github.com/custom-components/hacs/"
CUSTOM_UPDATER_LOCATIONS = [
    "{}/custom_components/custom_updater.py",
    "{}/custom_components/custom_updater/__init__.py",
]

ISSUE_URL = "{}issues".format(PROJECT_URL)
DOMAIN_DATA = "{}_data".format(NAME_SHORT.lower())

ELEMENT_TYPES = ["integration", "plugin"]

IFRAME = {
    "title": "Community",
    "icon": "mdi:alpha-c-box",
    "url": "/community_overview",
    "path": "community",
    "require_admin": True,
}


# Messages
CUSTOM_UPDATER_WARNING = """
This cannot be used with custom_updater.
To use this you need to remove custom_updater form {}
"""

DEV_MODE = "You have 'dev' enabled for HACS, this is not intended for regular use, no support will be given if you break something."

STARTUP = """
-------------------------------------------------------------------
{}
Version: {}
This is a custom integration
If you have any issues with this you need to open an issue here:
{}
-------------------------------------------------------------------
""".format(
    NAME_LONG, VERSION, ISSUE_URL
)