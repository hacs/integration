"""Helper to get default repositories."""
import json
from typing import List

from aiogithubapi import AIOGitHubAPIException

from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.helpers.functions.information import get_repository
from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.share import get_hacs


async def async_get_list_from_default(default: str) -> List:
    """Get repositories from default list."""
    hacs = get_hacs()
    repositories = []
    logger = getLogger("async_get_list_from_default")

    try:
        repo = await get_repository(
            hacs.session, hacs.configuration.token, "hacs/default",
        )
        content = await repo.get_contents(default, repo.default_branch)
        repositories = json.loads(content.content)

    except (AIOGitHubAPIException, HacsException) as exception:
        logger.error(exception)

    except (Exception, BaseException) as exception:
        logger.error(exception)

    logger.debug(f"Got {len(repositories)} elements for {default}")

    return repositories
