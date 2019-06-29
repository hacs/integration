"""Blueprint for HacsMigration."""
import logging
import json
from shutil import copy2

import aiofiles

from .hacsbase import HacsBase
from .const import STORAGE_VERSION, STORENAME

_LOGGER = logging.getLogger("custom_components.hacs.migration")


class HacsMigration(HacsBase):
    """HACS data migration handler."""

    _old = None

    async def validate(self):
        """Check the current storage version to determine if migration is needed."""
        self._old = await self.storage.get(True)

        if not self._old:
            # Could not read the current file, it probably does not exist.
            # Running full scan.
            await self.update_repositories()

        elif self._old["hacs"]["schema"] == "1":
            # Creating backup.
            source = "{}/.storage/hacs".format(self.config_dir)
            destination = "{}.1".format(source)
            _LOGGER.info("Backing up current file to '%s'", destination)
            copy2(source, destination)
            await self.from_1_to_2()

        elif self._old["hacs"]["schema"] == "2":
            # Creating backup.
            source = "{}/.storage/hacs".format(self.config_dir)
            destination = "{}.2".format(source)
            _LOGGER.info("Backing up current file to '%s'", destination)
            copy2(source, destination)
            await self.from_2_to_3()

        elif self._old["hacs"].get("schema") == STORAGE_VERSION:
            pass

        else:
            # Should not get here, but do a full scan just in case...
            await self.update_repositories()

        await self.flush_data()

    async def flush_data(self):
        """Flush validated data."""
        _LOGGER.info("Flushing data to storage.")

        datastore = "{}/.storage/{}".format(self.config_dir, STORENAME)

        try:
            async with aiofiles.open(
                datastore, mode="w", encoding="utf-8", errors="ignore"
            ) as outfile:
                await outfile.write(json.dumps(self._old, indent=4))
                outfile.close()

        except Exception as error:
            msg = "Could not write data to {} - {}".format(datastore, error)
            _LOGGER.error(msg)

    async def from_1_to_2(self):
        """Migrate from storage version 1 to storage version 2."""
        _LOGGER.info("Starting migration of HACS data from 1 to 2.")
        self.data = self._old

        for repository in self._old["repositories"]:
            self._old["repositories"][repository]["show_beta"] = False
        self._old["hacs"]["schema"] = "2"
        _LOGGER.info("Migration of HACS data from 1 to 2 is complete.")

    async def from_2_to_3(self):
        """Migrate from storage version 2 to storage version 3."""
        _LOGGER.info("Starting migration of HACS data from 2 to 3.")
        self.data = self._old

        for repository in self._old["repositories"]:
            if self._old["repositories"][repository]["installed"]:
                self._old["repositories"][repository]["new"] = False
        self._old["hacs"]["schema"] = "2"
        _LOGGER.info("Migration of HACS data from 2 to 3 is complete.")
