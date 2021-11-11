"""Custom Exceptions for HACS."""


class HacsException(Exception):
    """Super basic."""


class HacsRepositoryArchivedException(HacsException):
    """For repositories that are archived."""


class HacsNotModifiedException(HacsException):
    """For responses that are not modified."""


class HacsExpectedException(HacsException):
    """For stuff that are expected."""


class HacsRepositoryExistException(HacsException):
    """For repositories that are already exist."""


class HacsExecutionStillInProgress(HacsException):
    """Exception to raise if execution is still in progress."""
