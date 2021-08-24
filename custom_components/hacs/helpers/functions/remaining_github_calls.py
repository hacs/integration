"""Helper to calculate the remaining calls to github."""
import math
from aiogithubapi import GitHubAPI, GitHubAuthenticationException

from custom_components.hacs.utils.logger import getLogger

_LOGGER = getLogger()

RATE_LIMIT_THRESHOLD = 1000
CALLS_PR_REPOSITORY = 15


async def remaining(github: GitHubAPI):
    """Helper to calculate the remaining calls to github."""
    try:
        result = await github.rate_limit()
    except GitHubAuthenticationException as exception:
        _LOGGER.error(f"GitHub authentication failed - {exception}")
        return None
    except BaseException as exception:  # pylint: disable=broad-except
        _LOGGER.error(exception)
        return 0

    return result.data.resources.core.remaining or 0


async def get_fetch_updates_for(github: GitHubAPI):
    """Helper to calculate the number of repositories we can fetch data for."""
    if (limit := await remaining(github)) is None:
        return None

    if limit - RATE_LIMIT_THRESHOLD <= CALLS_PR_REPOSITORY:
        return 0
    return math.floor((limit - RATE_LIMIT_THRESHOLD) / CALLS_PR_REPOSITORY)
