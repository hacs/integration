"""Custom Exceptions."""


class HacsBaseException(Exception):
    """Super basic."""


class HacsUserScrewupException(HacsBaseException):
    """Raise this when the user does something they should not do."""


class HacsNotSoBasicException(HacsBaseException):
    """Not that basic."""


class HacsDataFileMissing(HacsBaseException):
    """Raise this storage datafile is missing."""


class HacsDataNotExpected(HacsBaseException):
    """Raise this when data returned from storage is not ok."""


class HacsRepositoryInfo(HacsBaseException):
    """Raise this when repository info is missing/wrong."""


class HacsRequirement(HacsBaseException):
    """Raise this when repository is missing a requirement."""


class HacsMissingManifest(HacsBaseException):
    """Raise this when manifest is missing."""

    def __init__(self, message="The manifest file is missing in the repository."):
        super().__init__(message)
        self.message = message


class HacsBlacklistException(HacsBaseException):
    """Raise this when the repository is currently in the blacklist."""

    def __init__(self, message="The repository is currently in the blacklist."):
        super().__init__(message)
        self.message = message
