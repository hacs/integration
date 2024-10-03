"""Special handler for container."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..strategy import AwesomeVersionStrategy

CONTAINER_VERSION_MAP = {"stable": 1, "beta": 2, "latest": 3, "dev": 4}

if TYPE_CHECKING:
    from awesomeversion import AwesomeVersion


def compare_handler_container(
    version_a: AwesomeVersion,
    version_b: AwesomeVersion,
) -> bool | None:
    """Compare handler container."""
    if version_a.strategy == AwesomeVersionStrategy.SPECIALCONTAINER:
        if version_b.strategy != AwesomeVersionStrategy.SPECIALCONTAINER:
            return True
        return (
            CONTAINER_VERSION_MAP[version_a.string]
            > CONTAINER_VERSION_MAP[version_b.string]
        )
    if version_b.strategy == AwesomeVersionStrategy.SPECIALCONTAINER:
        return False
    return None
