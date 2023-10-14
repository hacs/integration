"""Various URL utils for HACS."""
import re

GIT_SHA = re.compile(r"^[a-fA-F0-9]{40}$")


def asset_download(repository: str, version: str, filenme: str) -> str:
    """Generate a download URL for a release asset."""
    return f"https://github.com/{repository}/releases/download/{version}/{filenme}"


def archive_download(
    *,
    repository: str,
    version: str,
    variant: str = "heads",
    **_,
) -> str:
    """Generate a download URL for a repository zip."""
    if GIT_SHA.match(version):
        return f"https://github.com/{repository}/archive/{version}.zip"
    return f"https://github.com/{repository}/archive/refs/{variant}/{version}.zip"
