"""Helper to check if path is safe to remove."""
from pathlib import Path

from custom_components.hacs.share import get_hacs


def is_safe_to_remove(path: str) -> bool:
    """Helper to check if path is safe to remove."""
    hacs = get_hacs()
    paths = [
        Path(f"{hacs.core.config_path}/{hacs.configuration.appdaemon_path}"),
        Path(f"{hacs.core.config_path}/{hacs.configuration.netdaemon_path}"),
        Path(f"{hacs.core.config_path}/{hacs.configuration.plugin_path}"),
        Path(f"{hacs.core.config_path}/{hacs.configuration.python_script_path}"),
        Path(f"{hacs.core.config_path}/{hacs.configuration.theme_path}"),
        Path(f"{hacs.core.config_path}/custom_components/"),
    ]
    if Path(path) in paths:
        return False
    return True
