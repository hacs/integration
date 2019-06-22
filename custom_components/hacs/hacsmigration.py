"""Blueprint for HacsMigration."""
import logging
from shutil import copy2

from .hacsbase import HacsBase
from .const import STORAGE_VERSION, VERSION

_LOGGER = logging.getLogger("custom_components.hacs.migration")


class HacsMigration(HacsBase):
    """HACS data migration handler."""

    old = None

    async def validate(self):
        """Check the current storage version to determine if migration is needed."""
        self.old = await self.storage.get()

        if not self.old:
            # Could not read the current file, it probably does not exist.
            # Running full scan.
            await self.update_repositories()

        elif "schema" not in self.old["hacs"]:
            # Creating backup.
            source = "{}/.storage/hacs".format(self.config_dir)
            destination = "{}.none".format(source)
            _LOGGER.info("Backing up current file to '%s'", destination)
            copy2(source, destination)

            # Run migration.
            await self.from_none_to_1()

            # Run the rest.
            await self.update_repositories()

        elif self.old["hacs"]["schema"] == "1":
            # Creating backup.
            source = "{}/.storage/hacs".format(self.config_dir)
            destination = "{}.1".format(source)
            _LOGGER.info("Backing up current file to '%s'", destination)
            copy2(source, destination)
            await self.from_1_to_2()

        elif self.old["hacs"].get("schema") == STORAGE_VERSION:
            pass

        else:
            # Should not get here, but do a full scan just in case...
            await self.update_repositories()

    async def from_none_to_1(self):
        """Migrate from None (< 0.4.0) to storage version 1."""
        _LOGGER.info("Starting migration of HACS data from None to 1.")

        for item in self.old["elements"]:
            repodata = self.old["elements"][item]
            if repodata.get("isinstalled"):
                # Register new repository
                _LOGGER.info("Migrating %s", repodata["repo"])
                repository, setup_result = await self.register_new_repository(
                    repodata["element_type"], repodata["repo"]
                )

                repository.version_installed = repodata["installed_version"]
                repository.installed = True
                self.repositories[repository.repository_id] = repository

    async def from_1_to_2(self):
        """Migrate from storage version 1 to storage version 2."""
        _LOGGER.info("Starting migration of HACS data from 1 to 2.")

        for repository in self.repositories:
            repository = self.repositories[repository]
            repository.show_beta = False
            await repository.set_repository_releases()
            self.repositories[repository.repository_id] = repository
        self.data["hacs"]["schema"] = "2"
        _LOGGER.info("Migration of HACS data from 1 to 2 is complete.")
