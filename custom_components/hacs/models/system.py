"""HACS System info."""
import attr
from ..enums import HacsStage
from ..const import INTEGRATION_VERSION


@attr.s
class HacsSystem:
    """HACS System info."""

    disabled: bool = False
    running: bool = False
    version: str = INTEGRATION_VERSION
    stage: HacsStage = attr.ib(HacsStage)
    action: bool = False
