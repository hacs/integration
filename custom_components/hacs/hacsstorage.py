"""Blueprint for HacsStorage."""
# pylint: disable=broad-except
import logging
import json
import aiofiles
from custom_components.hacs.blueprints import HacsBase

_LOGGER = logging.getLogger('custom_components.hacs.storage')


class HacsStorage(HacsBase):
    """HACS storage handler."""

    async def get(self):
        """Read HACS data to storage."""
        from custom_components.hacs.blueprints import (
            HacsRepositoryIntegration,
            HacsRepositoryPlugin,)
        datastore = "{}/.storage/{}".format(self.config_dir, self.const.STORENAME)
        _LOGGER.debug("Reading from datastore %s.", datastore)

        try:
            self.data["task_running"] = True
            async with aiofiles.open(
                datastore, mode='r', encoding="utf-8", errors="ignore") as datafile:
                store_data = await datafile.read()
                store_data = json.loads(store_data)
                datafile.close()

            # Restore data about HACS
            self.data["hacs"] = store_data["hacs"]

            # Restore repository data
            for repository in store_data["repositories"]:
                # Set var
                repositorydata = store_data["repositories"][repository]

                _LOGGER.info("Loading %s from storage.", repositorydata["repository_name"])

                # Restore integration
                if repositorydata["repository_type"] == "integration":
                    repository = HacsRepositoryIntegration(repositorydata["repository_name"])

                # Restore plugin
                elif repositorydata["repository_type"] == "plugin":
                    repository = HacsRepositoryPlugin(repositorydata["repository_name"])

                # Not supported
                else:
                    continue

                # Attach AIOGitHub object
                await repository.set_repository()

                # Set repository attributes from stored values
                for attribute in repositorydata:
                    repository.__setattr__(attribute, repositorydata[attribute])

                # Restore complete
                self.repositories[repository.repository_id] = repository

        except Exception as exception:
            msg = "Could not load data from {} - {}".format(datastore, exception)
            _LOGGER.error(msg)
        self.data["task_running"] = False


    async def set(self):
        """Write HACS data to storage."""
        datastore = "{}/.storage/{}".format(self.config_dir, self.const.STORENAME)

        data = {}
        data["hacs"] = self.data["hacs"]

        data["repositories"] = {}

        for repository in self.repositories:
            repositorydata = {}
            repository = self.repositories[repository]

            repositorydata["hide"] = repository.hide
            repositorydata["installed"] = repository.installed
            repositorydata["name"] = repository.name
            repositorydata["repository_name"] = repository.repository_name
            repositorydata["repository_type"] = repository.repository_type
            repositorydata["show_beta"] = repository.show_beta
            repositorydata["version_installed"] = repository.version_installed

            data["repositories"][repository.repository_id] = repositorydata

        try:
            async with aiofiles.open(
                datastore, mode='w', encoding="utf-8", errors="ignore") as outfile:
                await outfile.write(json.dumps(data, indent=4))
                outfile.close()

        except Exception as error:
            msg = "Could not write data to {} - {}".format(datastore, error)
            _LOGGER.error(msg)
