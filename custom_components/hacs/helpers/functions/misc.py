"""Helper functions: misc"""
import re
import semantic_version
from functools import lru_cache

RE_REPOSITORY = re.compile(
    r"(?:(?:.*github.com.)|^)([A-Za-z0-9-]+\/[\w.-]+?)(?:(?:\.git)?|(?:[^\w.-].*)?)$"
)


def get_repository_name(repository) -> str:
    """Return the name of the repository for use in the frontend."""

    if repository.repository_manifest.name is not None:
        return repository.repository_manifest.name

    if repository.data.category == "integration":
        if repository.integration_manifest:
            if "name" in repository.integration_manifest:
                return repository.integration_manifest["name"]

    return (
        repository.data.full_name.split("/")[-1]
        .replace("-", " ")
        .replace("_", " ")
        .title()
    )


@lru_cache(maxsize=1024)
def version_left_higher_then_right(new: str, old: str) -> bool:
    """Return a bool if source is newer than target, will also be true if identical."""
    if not isinstance(new, str) or not isinstance(old, str):
        return False
    if new == old:
        return True
    return semantic_version.Version.coerce(new) > semantic_version.Version.coerce(old)


def extract_repository_from_url(url: str) -> str or None:
    """Extract the owner/repo part form a URL."""
    match = re.match(RE_REPOSITORY, url)
    if not match:
        return None
    return match.group(1).lower()
