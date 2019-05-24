"""Custom Exceptions."""

class HacsBaseException(Exception):
    """Super basic."""
    pass

class HacsNotSoBasicException(HacsBaseException):
    """Not that basic."""
    pass

class HacsMissingManifest(HacsBaseException):
    """Not that basic."""
    pass

class HacsDataFileMissing(HacsBaseException):
    """Not that basic."""
    pass

class HacsDataNotExpected(HacsBaseException):
    """Not that basic."""
    pass
