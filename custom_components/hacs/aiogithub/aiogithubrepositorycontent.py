"""AioGitHub: Repository Release"""
import base64


class AIOGithubRepositoryContent:
    """Repository Conetent Github API implementation."""

    def __init__(self, attributes):
        """Initialize."""
        self.attributes = attributes

    @property
    def type(self):
        return self.attributes.get("type", "file")

    @property
    def encoding(self):
        return self.attributes.get("encoding")

    @property
    def name(self):
        return self.attributes.get("name")

    @property
    def path(self):
        return self.attributes.get("path")

    @property
    def content(self):
        return base64.b64decode(
            bytearray(self.attributes.get("content"), "utf-8")
        ).decode()

    @property
    def download_url(self):
        return self.attributes.get("download_url") or self.attributes.get(
            "browser_download_url"
        )
