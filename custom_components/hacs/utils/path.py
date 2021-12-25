"""Path utils"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base import HacsBase


def is_safe(hacs: HacsBase, path: str | Path) -> bool:
    """Helper to check if path is safe to remove."""
    return Path(path).as_posix() not in (
        Path(f"{hacs.core.config_path}/{hacs.configuration.appdaemon_path}").as_posix(),
        Path(f"{hacs.core.config_path}/{hacs.configuration.netdaemon_path}").as_posix(),
        Path(f"{hacs.core.config_path}/{hacs.configuration.plugin_path}").as_posix(),
        Path(f"{hacs.core.config_path}/{hacs.configuration.python_script_path}").as_posix(),
        Path(f"{hacs.core.config_path}/{hacs.configuration.theme_path}").as_posix(),
        Path(f"{hacs.core.config_path}/custom_components/").as_posix(),
    )
