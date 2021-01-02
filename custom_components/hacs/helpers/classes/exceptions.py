"""Custom Exceptions."""


class HacsException(Exception):
    """Super basic."""


class HacsRepositoryArchivedException(HacsException):
    """For repositories that are archived."""


class HacsExpectedException(HacsException):
    """For stuff that are expected."""
