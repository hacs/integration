"""Various URL utils for HACS."""

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
    return f"https://github.com/{repository}/archive/refs/{variant}/{version}.zip"
