"""Patch time related functions."""
from __future__ import annotations

import datetime
import freezegun

from homeassistant import util
from homeassistant.util import dt as dt_util

class CustomFakeDatetime(freezegun.api.FakeDatetime):  # type: ignore[name-defined]
    """Modified to workaround tz problem."""

    @classmethod
    def _tz_offset(cls):
        return datetime.timedelta(hours=0)


def _utcnow() -> datetime.datetime:
    """Make utcnow patchable by freezegun."""
    return datetime.datetime.now(tz=datetime.UTC)


dt_util.utcnow = _utcnow  # type: ignore[assignment]
util.utcnow = _utcnow  # type: ignore[assignment]
freezegun.api.FakeDatetime = CustomFakeDatetime

