"""Version utils."""
from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from awesomeversion import (
    AwesomeVersion,
    AwesomeVersionException,
    AwesomeVersionStrategy,
)

if TYPE_CHECKING:
    from ..repositories.base import HacsRepository


@lru_cache(maxsize=1024)
def version_left_higher_then_right(left: str, right: str) -> bool:
    """Return a bool if source is newer than target, will also be true if identical."""
    try:
        left_version = AwesomeVersion(left)
        right_version = AwesomeVersion(right)
        if (
            left_version.strategy != AwesomeVersionStrategy.UNKNOWN
            and right_version.strategy != AwesomeVersionStrategy.UNKNOWN
        ):
            return left_version > right_version
    except (AwesomeVersionException, AttributeError):
        pass

    return None


def version_left_higher_or_equal_then_right(left: str, right: str) -> bool:
    """Return a bool if source is newer than target, will also be true if identical."""
    if left == right:
        return True

    return version_left_higher_then_right(left, right)


def version_to_download(repository: HacsRepository) -> str:
    """Determine which version to download."""
    if repository.data.last_version is not None:
        if repository.data.selected_tag is not None:
            if repository.data.selected_tag == repository.data.last_version:
                repository.data.selected_tag = None
                return repository.data.last_version
            return repository.data.selected_tag
        return repository.data.last_version

    if repository.data.selected_tag is not None:
        if repository.data.selected_tag == repository.data.default_branch:
            return repository.data.default_branch
        if repository.data.selected_tag in repository.data.published_tags:
            return repository.data.selected_tag

    return repository.data.default_branch or "main"
