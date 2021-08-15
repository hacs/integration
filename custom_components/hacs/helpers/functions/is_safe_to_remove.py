"""Helper to check if path is safe to remove."""
from custom_components.hacs.share import get_hacs

from ...utils.path import is_safe


def is_safe_to_remove(path: str) -> bool:
    """Helper to check if path is safe to remove."""
    hacs = get_hacs()
    return is_safe(hacs, path)
