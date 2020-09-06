"""HACS System info."""
import attr
from .stage import HacsStage


@attr.s
class HacsSystem:
    """HACS System info."""

    disabled: bool = False
    running: bool = False
    stage = attr.ib(HacsStage)
