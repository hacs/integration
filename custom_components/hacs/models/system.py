"""HACS System info."""
from typing import Optional
import attr

from ..const import INTEGRATION_VERSION
from ..enums import HacsStage


@attr.s
class HacsSystem:
    """HACS System info."""

    disabled: bool = False
    disabled_reason: Optional[str] = None
    running: bool = False
    version: str = INTEGRATION_VERSION
    stage: HacsStage = attr.ib(HacsStage)
    action: bool = False
