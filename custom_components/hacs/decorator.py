from functools import wraps
import logging

_LOGGER: logging.Logger = logging.getLogger("custom_components.hacs.setup")


def announceSetup(task):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            _LOGGER.info(task)
            return await func(*args, **kwargs)

        return wrapper

    return decorator