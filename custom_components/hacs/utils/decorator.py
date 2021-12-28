"""HACS Decorators."""
import asyncio
from functools import wraps
from typing import Any, Coroutine

from ..const import DEFAULT_CONCURRENT_BACKOFF_TIME, DEFAULT_CONCURRENT_TASKS


def concurrent(
    concurrenttasks: int = DEFAULT_CONCURRENT_TASKS,
    backoff_time=DEFAULT_CONCURRENT_BACKOFF_TIME,
) -> Coroutine[Any, Any, None]:
    """Return a modified function."""

    max_concurrent = asyncio.Semaphore(concurrenttasks)

    def inner_function(function) -> Coroutine[Any, Any, None]:
        @wraps(function)
        async def wrapper(*args, **kwargs) -> None:

            async with max_concurrent:
                await function(*args, **kwargs)
                await asyncio.sleep(backoff_time)

        return wrapper

    return inner_function
