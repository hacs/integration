"""Init file for aiohasupervisor."""

from aiohasupervisor.exceptions import (
    SupervisorAuthenticationError,
    SupervisorBadRequestError,
    SupervisorConnectionError,
    SupervisorError,
    SupervisorForbiddenError,
    SupervisorNotFoundError,
    SupervisorResponseError,
    SupervisorServiceUnavailableError,
    SupervisorTimeoutError,
)
from aiohasupervisor.root import SupervisorClient

__all__ = [
    "SupervisorError",
    "SupervisorConnectionError",
    "SupervisorAuthenticationError",
    "SupervisorBadRequestError",
    "SupervisorForbiddenError",
    "SupervisorNotFoundError",
    "SupervisorResponseError",
    "SupervisorServiceUnavailableError",
    "SupervisorTimeoutError",
    "SupervisorClient",
]
