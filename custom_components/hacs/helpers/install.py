"""Install helper for repositories."""
import os
import tempfile
from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.hacsbase.backup import Backup


async def install_repository(repository):
    """Common installation steps of the repository."""
    persistent_directory = None
    await repository.update_repository()

    if not repository.can_install:
        raise HacsException(
            "The version of Home Assistant is not compatible with this version"
        )

    version = version_to_install(repository)
    if version == repository.information.default_branch:
        repository.ref = version
    else:
        repository.ref = f"tags/{version}"

    if repository.repository_manifest:
        if repository.repository_manifest.persistent_directory:
            if os.path.exists(
                f"{repository.content.path.local}/{repository.repository_manifest.persistent_directory}"
            ):
                persistent_directory = Backup(
                    f"{repository.content.path.local}/{repository.repository_manifest.persistent_directory}",
                    tempfile.gettempdir() + "/hacs_persistent_directory/",
                )
                persistent_directory.create()

    if repository.status.installed and not repository.content.single:
        backup = Backup(repository.content.path.local)
        backup.create()

    if (
        repository.repository_manifest.zip_release
        and version != repository.information.default_branch
    ):
        validate = await repository.download_zip(repository.validate)
    else:
        validate = await repository.download_content(
            repository.validate,
            repository.content.path.remote,
            repository.content.path.local,
            repository.ref,
        )

    if validate.errors:
        for error in validate.errors:
            repository.logger.error(error)
        if repository.status.installed and not repository.content.single:
            backup.restore()

    if repository.status.installed and not repository.content.single:
        backup.cleanup()

    if persistent_directory is not None:
        persistent_directory.restore()
        persistent_directory.cleanup()

    if validate.success:
        if repository.information.full_name not in repository.common.installed:
            if repository.information.full_name == "hacs/integration":
                repository.common.installed.append(repository.information.full_name)
        repository.status.installed = True
        repository.versions.installed_commit = repository.versions.available_commit

        if version == repository.information.default_branch:
            repository.versions.installed = None
        else:
            repository.versions.installed = version

        await reload_after_install(repository)
        installation_complete(repository)


async def reload_after_install(repository):
    """Reload action after installation success."""
    if repository.information.category == "integration":
        if repository.config_flow:
            if repository.information.full_name != "hacs/integration":
                await repository.reload_custom_components()
        repository.pending_restart = True

    elif repository.information.category == "theme":
        try:
            await repository.hass.services.async_call("frontend", "reload_themes", {})
        except Exception:  # pylint: disable=broad-except
            pass


def installation_complete(repository):
    """Action to run when the installation is complete."""
    repository.hass.bus.async_fire(
        "hacs/repository",
        {
            "id": 1337,
            "action": "install",
            "repository": repository.information.full_name,
        },
    )


def version_to_install(repository):
    """Determine which version to isntall."""
    if repository.versions.available is not None:
        if repository.status.selected_tag is not None:
            if repository.status.selected_tag == repository.versions.available:
                repository.status.selected_tag = None
                return repository.versions.available
            return repository.status.selected_tag
        return repository.versions.available
    if repository.status.selected_tag is not None:
        if repository.status.selected_tag == repository.information.default_branch:
            return repository.information.default_branch
        if repository.status.selected_tag in repository.releases.published_tags:
            return repository.status.selected_tag
    if repository.information.default_branch is None:
        return "master"
    return repository.information.default_branch
