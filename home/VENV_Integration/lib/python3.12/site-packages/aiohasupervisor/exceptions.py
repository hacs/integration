"""Exceptions from supervisor client."""


class SupervisorError(Exception):
    """Generic exception."""

    def __init__(self, message: str | None = None, job_id: str | None = None) -> None:
        """Initialize exception."""
        if message is not None:
            super().__init__(message)
        else:
            super().__init__()

        self.job_id: str | None = job_id


class SupervisorConnectionError(SupervisorError, ConnectionError):
    """Unknown error connecting to supervisor."""


class SupervisorTimeoutError(SupervisorError, TimeoutError):
    """Timeout connecting to supervisor."""


class SupervisorBadRequestError(SupervisorError):
    """Invalid request made to supervisor."""


class SupervisorAuthenticationError(SupervisorError):
    """Invalid authentication sent to supervisor."""


class SupervisorForbiddenError(SupervisorError):
    """Client is not allowed to take the action requested."""


class SupervisorNotFoundError(SupervisorError):
    """Requested resource does not exist."""


class SupervisorServiceUnavailableError(SupervisorError):
    """Cannot complete request because a required service is unavailable."""


class SupervisorResponseError(SupervisorError):
    """Unusable response received from Supervisor with the wrong type or encoding."""
