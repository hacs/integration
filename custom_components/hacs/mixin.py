"""Mixin classes."""
# pylint: disable=too-few-public-methods
from __future__ import annotations

from logging import Logger

from .utils.logger import getLogger


class LogMixin:
    """Mixin to provide 'self.log' to classes."""

    log: Logger = getLogger()
