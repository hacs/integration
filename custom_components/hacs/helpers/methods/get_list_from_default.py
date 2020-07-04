"""Helper to get default repositories."""
import json
import logging
from abc import ABC

from aiogithubapi import AIOGitHubAPIException

from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.globals import get_hacs
from custom_components.hacs.helpers.functions.information import get_repository


class GetListFromDefault(ABC):
    async def async_get_list_from_default(self, default: str) -> dict:
        """Get repositories from default list."""
        hacs = get_hacs()
        repositories = []
        logger = logging.getLogger("custom_components.hacs.async_get_list_from_default")

        try:
            repo = await get_repository(
                hacs.session, hacs.configuration.token, "hacs/default",
            )
            content = await repo.get_contents(default, repo.default_branch)
            repositories = json.loads(content.content)

        except (AIOGitHubAPIException, HacsException) as exception:
            logger.error(exception)

        except Exception as exception:
            logger.error(exception)

        logger.debug(f"Got {len(repositories)} repositories from {default}")

        return repositories
