"""Blueprint for HacsMigration."""
import logging
from custom_components.hacs.hacsbase import HacsBase

_LOGGER = logging.getLogger('custom_components.hacs.migration')


class HacsMigration(HacsBase):
    """HACS data migration handler."""

    old = None

    async def validate(self):
        """Check the current storage version to determine if migration is needed."""
        self.old = await self.storage.get()
        if not self.old["hacs"].get("schema"):
            # TODO: Create backup
            await self.from_none_to_1()

    async def from_none_to_1(self):
        """Migrate from None (< 0.4.0) to storage version 1."""
        _LOGGER.info("Starting migration of HACS data from None to 1.")

        for item in self.old["elements"]:
            repodata = self.old["elements"][item]
            if repodata.get("isinstalled"):
                # Register new repository
                _LOGGER.info("Migrating %s", repodata["repo"])
                repository, setup_result = await self.register_new_repository(repodata["element_type"], repodata["repo"])

                if setup_result:
                    # Set old values
                    repository.version_installed = repodata["installed_version"]

        self.data["hacs"]["schema"] = "1"

        # TODO: Verify that this is actually needed.
        #for repository_type in self.old["repos"]:
        #    repository_type = self.old["repos"][repository_type]
        #    for repository in repository_type:
        #        # Register new repository
        #        _LOGGER.info("Migrating %s", repository)
        #        repository, setup_result = await self.register_new_repository(repodata["element_type"], repodata["repo"])
