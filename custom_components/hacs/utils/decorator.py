"""HACS decorators."""


from aiogithubapi import GitHubAuthenticationException, GitHubNotModifiedException, GitHubException

from ..enums import HacsDisabledReason

from ..base import HacsBase
from ..exceptions import HacsException


def GitHubAPI(github_api_call_function):  # pylint: disable=invalid-name
    """Decorator to catch Github API errors."""

    async def github_api_wrapper(*args, **kwargs):
        hacs: HacsBase = args[0].hacs
        if hacs.system.disabled:
            raise HacsException(f"HACS is disabled - {hacs.system.disabled_reason}")
        try:
            return await github_api_call_function(*args, **kwargs)
        except GitHubAuthenticationException as exception:
            hacs.disable_hacs(HacsDisabledReason.INVALID_TOKEN)
            raise HacsException(exception) from exception
        except GitHubNotModifiedException as exception:
            raise exception
        except GitHubException as exception:
            raise HacsException(exception) from exception

    return github_api_wrapper
