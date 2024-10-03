import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import psutil  # noqa: F401


class PsutilWrapper():
    """Wrap a copy of psutil."""

    def __init__(self) -> None:
        psutil_spec = importlib.util.find_spec("psutil")
        assert psutil_spec and psutil_spec.loader
        psutil_module = importlib.util.module_from_spec(psutil_spec)
        psutil_spec.loader.exec_module(psutil_module)
        self.psutil: psutil = psutil_module
