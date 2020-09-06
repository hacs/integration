"""Lovelace Modes."""
from enum import Enum


class LovelaceMode(str, Enum):
    """Lovelace Modes."""

    STORAGE = "storage"
    AUTO = "auto"
    YAML = "yaml"
