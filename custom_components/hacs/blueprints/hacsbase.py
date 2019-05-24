"""Blueprint for HacsBase."""
# pylint: disable=too-few-public-methods

class HacsBase:
    """The base class of HACS, nested thoughout the project."""
    data = {}
    hass = None
    github = None
    blacklist = []
    elements = []
    task_running = False
