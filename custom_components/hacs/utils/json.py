"""JSON utils."""

try:
    # Could be removed after 2022.06 is the min version
    # But in case Home Assistant changes, keep this try/except here...
    from homeassistant.helpers.json import json_loads
except ImportError:
    from json import loads as json_loads

__all__ = ["json_loads"]
