"""Blueprint for HacsStorage."""
# pylint: disable=broad-except
import logging
import json
import aiofiles
from .aiogithub import AIOGitHubException
from .hacsbase import HacsBase
from .exceptions import HacsNotSoBasicException, HacsRequirement
from .const import STORENAME, GENERIC_ERROR, STORAGE_VERSION

_LOGGER = logging.getLogger("custom_components.hacs.storage")


class HacsStorage(HacsBase):
    """HACS storage handler."""

    async def get(self):
        """Read HACS data to storage."""
        from .blueprints import (
            HacsRepositoryAppDaemon,
            HacsRepositoryIntegration,
            HacsRepositoryPlugin,
            HacsRepositoryPythonScripts,
            HacsRepositoryThemes,
        )

        datastore = "{}/.storage/{}".format(self.config_dir, STORENAME)
        _LOGGER.debug("Reading from datastore %s.", datastore)

        self.data["task_running"] = True
        try:
            async with aiofiles.open(
                datastore, mode="r", encoding="utf-8", errors="ignore"
            ) as datafile:
                store_data = await datafile.read()
                store_data = json.loads(store_data)
                datafile.close()
        except Exception:
            # Issues reading the file (if it exists.)
            return False

        # Restore data about HACS
        self.data["hacs"]["schema"] = store_data["hacs"].get("schema")
        self.data["hacs"]["view"] = store_data["hacs"].get("view")

        # Nothing to see here.
        if "repositories" not in store_data:
            return store_data

        # Re enable stored custom repositories.
        for repository in store_data["repositories"]:
            repository = store_data["repositories"][repository]
            if not repository.get("custom"):
                continue
            repository, status = await self.register_new_repository(
                repository["repository_type"], repository["repository_name"]
            )
            if status:
                repository = await self.restore(store_data, repository)
                if repository.show_beta:
                    await repository.set_repository_releases()

        # Get new repository objects
        appdaemon, integrations, plugins, python_scripts, themes = (
            await self.get_repositories()
        )

        repository_types = {
            "appdaemon": appdaemon,
            "integration": integrations,
            "plugin": plugins,
            "python_script": python_scripts,
            "theme": themes,
        }

        for repository_type in repository_types:
            for repository in repository_types[repository_type]:
                if repository.archived:
                    continue
                elif repository.full_name in self.blacklist:
                    continue
                elif repository.id in self.repositories:
                    continue
                else:
                    _LOGGER.info("Loading %s", repository.full_name)
                    if repository_type == "appdaemon":
                        repository = HacsRepositoryAppDaemon(
                            repository.full_name, repository
                        )
                    elif repository_type == "integration":
                        repository = HacsRepositoryIntegration(
                            repository.full_name, repository
                        )
                    elif repository_type == "plugin":
                        repository = HacsRepositoryPlugin(
                            repository.full_name, repository
                        )
                    elif repository_type == "python_script":
                        repository = HacsRepositoryPythonScripts(
                            repository.full_name, repository
                        )
                    elif repository_type == "theme":
                        repository = HacsRepositoryThemes(
                            repository.full_name, repository
                        )
                    else:
                        raise HacsNotSoBasicException(GENERIC_ERROR)

                    # Initial setup.
                    try:
                        await repository.setup_repository()
                    except (HacsRequirement, AIOGitHubException) as exception:
                        if not self.data["task_running"]:
                            _LOGGER.error(
                                "%s - %s", repository.repository_name, exception
                            )
                        self.blacklist.append(repository.repository_name)
                        continue

                    # Restore attributes
                    repository = await self.restore(store_data, repository)

                    # If BETA get the proper release
                    if repository.show_beta:
                        await repository.set_repository_releases()

                    # Restore complete
                    self.repositories[repository.repository_id] = repository

        self.data["task_running"] = False
        await self.set()
        return store_data

    async def set(self):
        """Write HACS data to storage."""
        if self.data["task_running"]:
            # BG task is running, skip store to this is done.
            return
        _LOGGER.info("Saving data")
        datastore = "{}/.storage/{}".format(self.config_dir, STORENAME)

        data = {}
        data["hacs"] = self.data["hacs"]
        data["hacs"]["schema"] = STORAGE_VERSION

        data["repositories"] = {}

        for repository in self.repositories:
            repositorydata = {}
            repository = self.repositories[repository]

            repositorydata["custom"] = repository.custom
            repositorydata["hide"] = repository.hide
            repositorydata["installed"] = repository.installed
            repositorydata["installed_commit"] = repository.installed_commit
            repositorydata["name"] = repository.name
            repositorydata["repository_name"] = repository.repository_name
            repositorydata["repository_type"] = repository.repository_type
            repositorydata["show_beta"] = repository.show_beta
            repositorydata["version_installed"] = repository.version_installed

            data["repositories"][repository.repository_id] = repositorydata

        try:
            async with aiofiles.open(
                datastore, mode="w", encoding="utf-8", errors="ignore"
            ) as outfile:
                await outfile.write(json.dumps(data, indent=4))
                outfile.close()

        except Exception as error:
            msg = "Could not write data to {} - {}".format(datastore, error)
            _LOGGER.error(msg)

    async def restore(self, store_data, repository):
        """Restore saved data to a repository object."""
        if str(repository.repository_id) not in store_data["repositories"]:
            return repository

        storeddata = store_data["repositories"][str(repository.repository_id)]

        # Set repository attributes from stored values
        for attribute in storeddata:
            if repository.repository_name == "custom-components/hacs":
                continue
            if attribute in ["custom"]:
                continue
            repository.__setattr__(attribute, storeddata[attribute])

        return repository
