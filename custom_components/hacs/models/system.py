"""HACS System info."""
from typing import Optional
import attr

from ..const import INTEGRATION_VERSION
from ..enums import HacsStage, HacsDisabledReason


@attr.s
class HacsSystem:
    """HACS System info."""

    disabled: bool = False
    disabled_reason: Optional[HacsDisabledReason] = None
    running: bool = False
    version: str = INTEGRATION_VERSION
    stage: HacsStage = attr.ib(HacsStage)
    action: bool = False

    @property
    def dict(self) -> dict:
        """Return as dict."""
        return {
            "disabled": self.disabled,
            "disabled_reason": self.disabled_reason,
            "running": self.running,
            "version": self.version,
            "stage": self.stage,
            "action": self.action,
        }
