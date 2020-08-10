# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
import os
import tempfile
from abc import ABC

from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.helpers.functions.download import download_content
from custom_components.hacs.helpers.functions.version_to_install import (
    version_to_install,
)
from custom_components.hacs.operational.backup import Backup, BackupNetDaemon


class RepositoryMethodPreInstall(ABC):
    async def async_pre_install(self) -> None:
        pass

    async def _async_pre_install(self) -> None:
        self.logger.info("Running pre installation steps")
        await self.async_pre_install()
        self.logger.info("Pre installation steps completed")


class RepositoryMethodInstall(ABC):
    async def async_install(self) -> None:
        await self._async_pre_install()
        self.logger.info("Running installation steps")
        await async_install_repository(self)
        self.logger.info("Installation steps completed")
        await self._async_post_install()


class RepositoryMethodPostInstall(ABC):
    async def async_post_installation(self) -> None:
        pass

    async def _async_post_install(self) -> None:
        self.logger.info("Running post installation steps")
        await self.async_post_installation()
        self.data.new = False
        self.hacs.hass.bus.async_fire(
            "hacs/repository",
            {"id": 1337, "action": "install", "repository": self.data.full_name},
        )
        self.logger.info("Post installation steps completed")


async def async_install_repository(repository):
    """Common installation steps of the repository."""
    persistent_directory = None
    await repository.update_repository()
    if repository.content.path.local is None:
        raise HacsException("repository.content.path.local is None")
    repository.validate.errors = []

    if not repository.can_install:
        raise HacsException(
            "The version of Home Assistant is not compatible with this version"
        )

    version = version_to_install(repository)
    if version == repository.data.default_branch:
        repository.ref = version
    else:
        repository.ref = f"tags/{version}"

    if repository.data.installed and repository.data.category == "netdaemon":
        persistent_directory = BackupNetDaemon(repository)
        persistent_directory.create()

    elif repository.data.persistent_directory:
        if os.path.exists(
            f"{repository.content.path.local}/{repository.data.persistent_directory}"
        ):
            persistent_directory = Backup(
                f"{repository.content.path.local}/{repository.data.persistent_directory}",
                tempfile.gettempdir() + "/hacs_persistent_directory/",
            )
            persistent_directory.create()

    if repository.data.installed and not repository.content.single:
        backup = Backup(repository.content.path.local)
        backup.create()

    if repository.data.zip_release and version != repository.data.default_branch:
        await repository.download_zip_files(repository)
    else:
        await download_content(repository)

    if repository.validate.errors:
        for error in repository.validate.errors:
            repository.logger.error(error)
        if repository.data.installed and not repository.content.single:
            backup.restore()

    if repository.data.installed and not repository.content.single:
        backup.cleanup()

    if persistent_directory is not None:
        persistent_directory.restore()
        persistent_directory.cleanup()

    if repository.validate.success:
        if repository.data.full_name not in repository.hacs.common.installed:
            if repository.data.full_name == "hacs/integration":
                repository.hacs.common.installed.append(repository.data.full_name)
        repository.data.installed = True
        repository.data.installed_commit = repository.data.last_commit

        if version == repository.data.default_branch:
            repository.data.installed_version = None
        else:
            repository.data.installed_version = version
