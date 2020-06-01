"""Install helper for repositories."""
import os
import tempfile
from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.hacsbase.backup import Backup, BackupNetDaemon
from custom_components.hacs.helpers.download import download_content


async def install_repository(repository):
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
        await repository.download_zip(repository)
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


def version_to_install(repository):
    """Determine which version to isntall."""
    if repository.data.last_version is not None:
        if repository.data.selected_tag is not None:
            if repository.data.selected_tag == repository.data.last_version:
                repository.data.selected_tag = None
                return repository.data.last_version
            return repository.data.selected_tag
        return repository.data.last_version
    if repository.data.selected_tag is not None:
        if repository.data.selected_tag == repository.data.default_branch:
            return repository.data.default_branch
        if repository.data.selected_tag in repository.data.published_tags:
            return repository.data.selected_tag
    if repository.data.default_branch is None:
        return "master"
    return repository.data.default_branch
