"""HACS decorators."""
import asyncio
from functools import wraps
from typing import Any, Coroutine

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


def concurrent(concurrenttasks=15, sleepafter=0) -> Coroutine[Any, Any, None]:
    """Return a modified function."""

    max_concurrent = asyncio.Semaphore(concurrenttasks)

    def inner_function(function) -> Coroutine[Any, Any, None]:
        if not asyncio.iscoroutinefunction(function):
            print("Is not a coroutine")
            return function

        @wraps(function)
        async def wrapper(*args) -> None:

            async with max_concurrent:
                await function(*args)
                await asyncio.sleep(sleepafter)

        return wrapper

    return inner_function
