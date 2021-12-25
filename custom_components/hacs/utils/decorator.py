"""HACS Decorators."""
import asyncio
from functools import wraps
from typing import Any, Coroutine


def concurrent(concurrenttasks=15, sleepafter=0) -> Coroutine[Any, Any, None]:
    """Return a modified function."""

    max_concurrent = asyncio.Semaphore(concurrenttasks)

    def inner_function(function) -> Coroutine[Any, Any, None]:
        if not asyncio.iscoroutinefunction(function):
            return function

        @wraps(function)
        async def wrapper(*args, **kwargs) -> None:

            async with max_concurrent:
                await function(*args, **kwargs)
                await asyncio.sleep(sleepafter)

        return wrapper

    return inner_function
