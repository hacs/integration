"""AioGitHub: Repository Release"""
from datetime import datetime
from .aiogithubrepositorycontent import AIOGithubRepositoryContent


class AIOGithubRepositoryRelease:
    """Repository Release Github API implementation."""

    def __init__(self, attributes):
        """Initialize."""
        self.attributes = attributes

    @property
    def tag_name(self):
        return self.attributes.get("tag_name")

    @property
    def name(self):
        return self.attributes.get("name")

    @property
    def published_at(self):
        return datetime.strptime(
            self.attributes.get("published_at"), "%Y-%m-%dT%H:%M:%SZ"
        )

    @property
    def draft(self):
        return self.attributes.get("draft")

    @property
    def prerelease(self):
        return self.attributes.get("prerelease")

    @property
    def assets(self):
        assetlist = []
        for item in self.attributes.get("assets"):
            assetlist.append(AIOGithubRepositoryContent(item))
        return assetlist
