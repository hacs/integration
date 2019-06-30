"""HACS overview objects."""
from ..hacsbase import HacsBase, HacsDataStore

class HacsFrontentOverview(HacsBase, HacsDataStore):
    """HacsFrontentOverview class."""

    @property
    def mode(self):
        """Return bool for which mode the frontend is in."""
        return self.frontend_mode
