"""Exceptions for AwesomeVersion."""


class AwesomeVersionException(Exception):
    """Base AwesomeVersion exception."""


class AwesomeVersionCompareException(AwesomeVersionException):
    """Thrown when compare is not possible."""


class AwesomeVersionStrategyException(AwesomeVersionException):
    """Thrown when the expected strategy does not match."""
