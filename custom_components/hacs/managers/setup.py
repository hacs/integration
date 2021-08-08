"""HACS setup module."""
from custom_components.hacs.base import HacsCommonManager


class HacsSetupManager(HacsCommonManager):
    """Hacs Setup manager."""

    entries_loaction = "setup_entries"
