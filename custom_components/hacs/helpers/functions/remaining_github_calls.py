"""Helper to calculate the remaining calls to github."""
import math

from custom_components.hacs.helpers.functions.logger import getLogger

_LOGGER = getLogger()


async def remaining(github):
    """Helper to calculate the remaining calls to github."""
    try:
        ratelimits = await github.get_rate_limit()
    except (BaseException, Exception) as exception:  # pylint: disable=broad-except
        _LOGGER.error(exception)
        return None
    if ratelimits.get("remaining") is not None:
        return int(ratelimits["remaining"])
    return 0


async def get_fetch_updates_for(github):
    """Helper to calculate the number of repositories we can fetch data for."""
    margin = 1000
    limit = await remaining(github)
    pr_repo = 15

    if limit is None:
        return None

    if limit - margin <= pr_repo:
        return 0
    return math.floor((limit - margin) / pr_repo)
