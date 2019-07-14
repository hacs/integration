"""AioGithub: Exceptions"""
class AIOGitHubException(BaseException):
    """Raise this when something is off."""


class AIOGitHubRatelimit(AIOGitHubException):
    """Raise this when we hit the ratelimit."""

class AIOGitHubAuthentication(AIOGitHubException):
    """Raise this when there is an authentication issue."""
