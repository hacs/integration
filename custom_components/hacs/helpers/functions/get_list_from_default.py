"""Helper to get default repositories."""
import json
from typing import List

from aiogithubapi import AIOGitHubAPIException

from ...enums import HacsCategory
from ...exceptions import HacsException
from ...share import get_hacs


async def async_get_list_from_default(default: HacsCategory) -> List:
    """Get repositories from default list."""
    hacs = get_hacs()
    try:
        content = await hacs.default.get_contents(default, hacs.default.default_branch)
        repositories = json.loads(content.content)

    except (AIOGitHubAPIException, HacsException) as exception:
        hacs.log.error(exception)

    except (Exception, BaseException) as exception:
        hacs.log.error(exception)
    else:
        hacs.log.debug("Got %s elements for %s", len(repositories), default)
        return repositories

    return []
