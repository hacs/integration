"""Blueprint for HacsMigration."""
import logging
import aiofiles
from custom_components.hacs import hacs

_LOGGER = logging.getLogger('custom_components.hacs.migration')


class HacsMigration(hacs):
    """HACS data migration handler."""
    old = None

    async def validate(self):
        """Check the current storage version to determine if migration is needed."""
        self.old = await self.storage.get()

    async def from_none_to_1(self):
        """Migrate from None (< 0.3.0) to storage version 1."""
        _LOGGER.info("Starting migration of HACS data from None to 1.")

        for item in self.old:
            repodata = self.old[item]
            if repodata.get("isinstalled"):
                # Register new repository
                _LOGGER.info("Migrating %s", repodata["repo"])
                repository, setup_result = await self.register_new_repository(repodata["element_type"], repodata["repo"])

                if setup_result:
                    # Set old values
                    repository.version_installed = repodata["installed_version"]
