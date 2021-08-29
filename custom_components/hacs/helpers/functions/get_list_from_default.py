"""Helper to get default repositories."""
from typing import List

from aiogithubapi import (
    GitHubAuthenticationException,
    GitHubNotModifiedException,
    GitHubRatelimitException,
)

from custom_components.hacs.const import REPOSITORY_HACS_DEFAULT
from custom_components.hacs.enums import HacsCategory, HacsDisabledReason
from custom_components.hacs.share import get_hacs


async def async_get_list_from_default(default: HacsCategory) -> List:
    """Get repositories from default list."""
    hacs = get_hacs()
    repositories = []

    try:
        repositories = await hacs.async_github_get_hacs_default_file(default)
        hacs.log.debug("Got %s elements for %s", len(repositories), default)
    except GitHubNotModifiedException:
        hacs.log.debug("Content did not change for %s/%s", REPOSITORY_HACS_DEFAULT, default)

    except GitHubRatelimitException as exception:
        hacs.log.error(exception)
        hacs.disable_hacs(HacsDisabledReason.RATE_LIMIT)

    except GitHubAuthenticationException as exception:
        hacs.log.error(exception)
        hacs.disable_hacs(HacsDisabledReason.INVALID_TOKEN)

    except BaseException as exception:  # pylint: disable=broad-except
        hacs.log.error(exception)

    return repositories
