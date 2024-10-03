"""Shim class to not have to depend on typing module in prod."""
# mypy: ignore-errors
import sys
import warnings
from typing import Any

warnings.warn(
    "josepy.magic_typing is deprecated and will be removed in a future release.", DeprecationWarning
)


class TypingClass:
    """Ignore import errors by getting anything"""

    def __getattr__(self, name: str) -> Any:
        return None


try:
    # mypy doesn't respect modifying sys.modules
    from typing import *  # noqa: F401,F403
except ImportError:
    sys.modules[__name__] = TypingClass()
