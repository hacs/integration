"""Helper to do common validation for repositories."""
from aiogithubapi import AIOGitHubException
from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.helpers.install import version_to_install
from custom_components.hacs.helpers.information import (
    get_repository,
    get_tree,
    get_releases,
)


async def common_validate(hacs, repository):
    """Common validation steps of the repository."""
    repository.validate.errors = []

    # Step 1: Make sure the repository exist.
    repository.logger.debug("Checking repository.")
    try:
        repository_object = await get_repository(
            hacs.session, hacs.configuration.token, repository.information.full_name
        )
        repository.repository_object = repository_object
        repository.data = repository.data.create_from_dict(repository_object.attributes)
    except (AIOGitHubException, HacsException) as exception:
        if not hacs.system.status.startup:
            repository.logger.error(exception)
        repository.validate.errors.append("Repository does not exist.")
        raise HacsException(exception)

    if repository.ref is None:
        repository.ref = version_to_install(repository)

    try:
        repository.tree = await get_tree(repository.repository_object, repository.ref)
        if not repository.tree:
            raise HacsException("No files in tree")
        repository.treefiles = []
        for treefile in repository.tree:
            repository.treefiles.append(treefile.full_path)
    except (AIOGitHubException, HacsException) as exception:
        if not hacs.system.status.startup:
            repository.logger.error(exception)
        raise HacsException(exception)

    # Step 2: Make sure the repository is not archived.
    if repository.data.archived:
        repository.validate.errors.append("Repository is archived.")
        raise HacsException("Repository is archived.")

    # Step 3: Make sure the repository is not in the blacklist.
    if repository.data.full_name in hacs.common.blacklist:
        repository.validate.errors.append("Repository is in the blacklist.")
        raise HacsException("Repository is in the blacklist.")

    # Step 5: Get releases.
    try:
        releases = await get_releases(
            repository.repository_object,
            repository.status.show_beta,
            hacs.configuration.release_limit,
        )
        if releases:
            repository.releases.releases = True
            repository.releases.published_tags = [x.tag_name for x in releases]
            repository.versions.available = next(iter(releases)).tag_name
            assets = next(iter(releases)).assets
            if assets:
                downloads = next(iter(assets)).attributes.get("download_count")
                repository.releases.downloads = downloads

    except (AIOGitHubException, HacsException):
        repository.releases.releases = False

    # Step 6: Get the content of hacs.json
    await repository.get_repository_manifest_content()

    # Set repository name
    repository.information.name = repository.information.full_name.split("/")[1]
