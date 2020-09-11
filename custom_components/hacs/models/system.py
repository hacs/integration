"""HACS System info."""
import attr
from ..enums import HacsStage
from ..const import VERSION


@attr.s
class HacsSystem:
    """HACS System info."""

    disabled: bool = False
    running: bool = False
    version: str = VERSION
    stage: HacsStage = attr.ib(HacsStage)
    action: bool = False
