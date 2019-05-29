"""Blueprint for HacsStorage."""
import aiofiles
from custom_components.hacs import hacs


class HacsStorage(hacs):
    """HACS storage handler."""

    async def get(self):
        """Read HACS data from storage."""

    async def set(self):
        """Write HACS data to storage."""
