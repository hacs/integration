"""Constants for HACS"""
VERSION = "0.2.1"
NAME_LONG = "HACS (Home Assistant Community Store)"
NAME_SHORT = "HACS"
STORENAME = "hacs"
PROJECT_URL = "https://github.com/custom_components/hacs/"
CUSTOM_UPDATER_LOCATIONS = [
    "{}/custom_components/custom_updater.py",
    "{}/custom_components/custom_updater/__init__.py",
]
ISSUE_URL = "{}issues".format(PROJECT_URL)
DOMAIN_DATA = "{}_data".format(NAME_SHORT.lower())
SKIP = [
    "custom-cards/custom-card-helpers",
    "custom-cards/information",
    "custom-cards/config-template-card",
    "custom-components/hacs",
    "custom-components/blueprint",
    "custom-components/information",
]
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

STARTUP = """
-------------------------------------------------------------------
{}
Version: {}
This is a custom component
If you have any issues with this you need to open an issue here:
{}
-------------------------------------------------------------------
""".format(
    NAME_LONG, VERSION, ISSUE_URL
)

NO_ELEMENTS = "No elements to show."

ERROR = [
    "Luke, I am your father!",
    "Scruffy-looking nerfherder!",
    "'What' ain't no country I've ever heard of. They speak English in What?",
    "Nobody's gonna hurt anybody. We're gonna be like three little Fonzies here. And what's Fonzie like?",
    "Back off man, I'm a scientist",
    "Listen! You smell something?",
    "I am serious, and don't call me Shirley.",
    "I know kung fu.",
    "Ho-ho-ho. Now I have a machine gun.",
    "Kneel before Zod!",
    "Try not. Do, or do not. There is no try.",
    "If we knew what it was we were doing, it would not be called research, would it?",
    "Wait a minute, Doc. Ah… Are you telling me you built a time machine… out of a DeLorean?",
]
