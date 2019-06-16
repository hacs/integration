"""Constants for HACS"""
VERSION = "0.8.0"
NAME_LONG = "HACS (Home Assistant Community Store)"
NAME_SHORT = "HACS"
STORAGE_VERSION = "1"
STORENAME = "hacs"
PROJECT_URL = "https://github.com/custom-components/hacs/"
CUSTOM_UPDATER_LOCATIONS = [
    "{}/custom_components/custom_updater.py",
    "{}/custom_components/custom_updater/__init__.py",
]
GENERIC_ERROR = "Possible error codes: 1D10T, PICNIC, B0110CK5."
ISSUE_URL = "{}issues".format(PROJECT_URL)
DOMAIN_DATA = "{}_data".format(NAME_SHORT.lower())
BLACKLIST = [
    "custom-cards/boilerplate-card",
    "custom-cards/custom-card-helpers",
    "custom-cards/information",
    "custom-cards/tracker-card",
    "custom-components/blueprint",
    "custom-components/information",
    "custom-components/custom_updater",
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

NO_ELEMENTS = "No elements to show, open the store to install some awesome stuff."

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


################################
##  Extra default repositories #
################################

DEFAULT_REPOSITORIES = {
    "integration": ["StyraHem/ShellyForHASS", "isabellaalstrom/sensor.krisinformation"],
    "plugin": [
        "maykar/compact-custom-header",
        "maykar/lovelace-swipe-navigation",
        "peternijssen/lovelace-postnl-card",
        "nervetattoo/simple-thermostat",
        "nervetattoo/banner-card",
        "kalkih/mini-media-player",
        "kalkih/mini-graph-card",
        "finity69x2/fan-control-entity-row",
        "thomasloven/lovelace-card-mod",
        "thomasloven/lovelace-markdown-mod",
        "thomasloven/lovelace-slider-entity-row",
        "isabellaalstrom/krisinfo-card",
    ],
}
