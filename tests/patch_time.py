"""Patch time related functions.

Copied from Home Assistant Core.
"""
from __future__ import annotations

import datetime
import time

from homeassistant import runner, util
from homeassistant.util import dt as dt_util


def _utcnow() -> datetime.datetime:
    """Make utcnow patchable by freezegun."""
    return datetime.datetime.now(tz=datetime.UTC)


def _monotonic() -> float:
    """Make monotonic patchable by freezegun."""
    return time.monotonic()


dt_util.utcnow = _utcnow  # type: ignore[assignment]
util.utcnow = _utcnow  # type: ignore[assignment]
runner.monotonic = _monotonic  # type: ignore[assignment]
