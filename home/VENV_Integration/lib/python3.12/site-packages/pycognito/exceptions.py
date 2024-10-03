class WarrantException(Exception):
    """Base class for all pyCognito exceptions"""


class ForceChangePasswordException(WarrantException):
    """Raised when the user is forced to change their password"""


class TokenVerificationException(WarrantException):
    """Raised when token verification fails."""


class MFAChallengeException(WarrantException):
    """Raised when MFA is required."""

    def __init__(self, message, tokens, *args, **kwargs):
        super().__init__(message, tokens, *args, **kwargs)
        self.message = message
        self._tokens = tokens

    def get_tokens(self):
        return self._tokens


class SoftwareTokenMFAChallengeException(MFAChallengeException):
    """Raised when Software Token MFA is required."""


class SMSMFAChallengeException(MFAChallengeException):
    """Raised when SMS MFA is required."""
