"""Custom Exceptions."""


class HacsException(Exception):
    """Super basic."""


class HacsRepositoryArchivedException(HacsException):
    """For repos that are archived (so they raise warnings instead of errors)."""


class HacsExpectedException(HacsException):
    """For stuff that are expected."""
