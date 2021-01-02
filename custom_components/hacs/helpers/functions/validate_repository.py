"""Helper to do common validation for repositories."""
from aiogithubapi import AIOGitHubAPIException

from custom_components.hacs.helpers.classes.exceptions import (
    HacsException,
    HacsRepositoryArchivedException,
)
from custom_components.hacs.helpers.functions.information import (
    get_releases,
    get_repository,
    get_tree,
)
from custom_components.hacs.helpers.functions.version_to_install import (
    version_to_install,
)
from custom_components.hacs.share import get_hacs, is_removed


async def common_validate(repository, ignore_issues=False):
    """Common validation steps of the repository."""
    repository.validate.errors = []

    # Make sure the repository exist.
    repository.logger.debug("%s Checking repository.", repository)
    await common_update_data(repository, ignore_issues)

    # Step 6: Get the content of hacs.json
    await repository.get_repository_manifest_content()


async def common_update_data(repository, ignore_issues=False):
    """Common update data."""
    hacs = get_hacs()
    releases = []
    try:
        repository_object = await get_repository(
            hacs.session, hacs.configuration.token, repository.data.full_name
        )
        repository.repository_object = repository_object
        repository.data.update_data(repository_object.attributes)
    except (AIOGitHubAPIException, HacsException) as exception:
        if not hacs.status.startup:
            repository.logger.error("%s %s", repository, exception)
        if not ignore_issues:
            repository.validate.errors.append("Repository does not exist.")
            raise HacsException(exception) from None

    # Make sure the repository is not archived.
    if repository.data.archived and not ignore_issues:
        repository.validate.errors.append("Repository is archived.")
        raise HacsRepositoryArchivedException("Repository is archived.")

    # Make sure the repository is not in the blacklist.
    if is_removed(repository.data.full_name) and not ignore_issues:
        repository.validate.errors.append("Repository is in the blacklist.")
        raise HacsException("Repository is in the blacklist.")

    # Get releases.
    try:
        releases = await get_releases(
            repository.repository_object,
            repository.data.show_beta,
            hacs.configuration.release_limit,
        )
        if releases:
            repository.data.releases = True
            repository.releases.objects = [x for x in releases if not x.draft]
            repository.data.published_tags = [
                x.tag_name for x in repository.releases.objects
            ]
            repository.data.last_version = next(iter(repository.data.published_tags))

    except (AIOGitHubAPIException, HacsException):
        repository.data.releases = False

    if not repository.force_branch:
        repository.ref = version_to_install(repository)
    if repository.data.releases:
        for release in repository.releases.objects or []:
            if release.tag_name == repository.ref:
                assets = release.assets
                if assets:
                    downloads = next(iter(assets)).attributes.get("download_count")
                    repository.data.downloads = downloads

    repository.logger.debug(
        "%s Running checks against %s", repository, repository.ref.replace("tags/", "")
    )

    try:
        repository.tree = await get_tree(repository.repository_object, repository.ref)
        if not repository.tree:
            raise HacsException("No files in tree")
        repository.treefiles = []
        for treefile in repository.tree:
            repository.treefiles.append(treefile.full_path)
    except (AIOGitHubAPIException, HacsException) as exception:
        if not hacs.status.startup:
            repository.logger.error("%s %s", repository, exception)
        if not ignore_issues:
            raise HacsException(exception) from None
