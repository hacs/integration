"""Helper to get default repositories."""
import json
from typing import List

from aiogithubapi import AIOGitHubAPIException

from custom_components.hacs.enums import HacsCategory
from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.helpers.functions.information import get_repository
from custom_components.hacs.share import get_hacs


async def async_get_list_from_default(default: HacsCategory) -> List:
    """Get repositories from default list."""
    hacs = get_hacs()
    repositories = []

    try:
        repo, _ = await get_repository(
            hacs.session, hacs.configuration.token, "hacs/default", None
        )
        content = await repo.get_contents(default, repo.default_branch)
        repositories = json.loads(content.content)

    except (AIOGitHubAPIException, HacsException) as exception:
        hacs.log.error(exception)

    except (Exception, BaseException) as exception:
        hacs.log.error(exception)

    hacs.log.debug("Got %s elements for %s", len(repositories), default)

    return repositories
