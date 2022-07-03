"""JSON utils."""

try:
    from homeassistant.helpers.json import json_loads
except ImportError:
    from json import loads as json_loads

__all__ = ["json_loads"]
