"""Helper to calculate the remaining calls to github."""
import math


async def remaining(github):
    """Helper to calculate the remaining calls to github."""
    try:
        ratelimits = await github.get_rate_limit()
    except:  # pylint: disable=broad-except
        return 0
    if ratelimits.get("remaining") is not None:
        return int(ratelimits["remaining"])
    return 0


async def get_fetch_updates_for(github):
    """Helper to calculate the number of repositories we can fetch data for."""
    margin = 100
    limit = await remaining(github)
    pr_repo = 10

    if limit - margin <= pr_repo:
        return 0
    return math.floor((limit - margin) / pr_repo)
