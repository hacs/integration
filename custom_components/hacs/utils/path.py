"""Path utils"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import HacsBase, HacsConfiguration


@lru_cache(maxsize=1)
def _get_safe_paths(config_path: str, configuration: HacsConfiguration) -> set[str]:
    """Get safe paths."""
    return {
        Path(f"{config_path}/{configuration.appdaemon_path}").as_posix(),
        Path(f"{config_path}/{configuration.netdaemon_path}").as_posix(),
        Path(f"{config_path}/{configuration.plugin_path}").as_posix(),
        Path(f"{config_path}/{configuration.python_script_path}").as_posix(),
        Path(f"{config_path}/{configuration.theme_path}").as_posix(),
        Path(f"{config_path}/custom_components/").as_posix(),
        Path(f"{config_path}/custom_templates/").as_posix(),
    }


def is_safe(hacs: HacsBase, path: str | Path) -> bool:
    """Helper to check if path is safe to remove."""
    return Path(path).as_posix() not in _get_safe_paths(hacs.core.config_path, hacs.configuration)
