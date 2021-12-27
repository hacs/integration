"""Return repository information if any."""
from aiogithubapi import AIOGitHubAPIException

from ..exceptions import HacsException


async def get_tree(repository, ref):
    """Return the repository tree."""
    try:
        tree = await repository.get_tree(ref)
        return tree
    except (ValueError, AIOGitHubAPIException) as exception:
        raise HacsException(exception)


async def get_releases(repository, prerelease=False, returnlimit=5):
    """Return the repository releases."""
    try:
        releases = await repository.get_releases(prerelease, returnlimit)
        return releases
    except (ValueError, AIOGitHubAPIException) as exception:
        raise HacsException(exception)
