from pathlib import Path

from .engine import RbnfEngine, RulesetName

_DIR = Path(__file__).parent

__version__ = (_DIR / "VERSION").read_text(encoding="utf-8").strip()

__all__ = [
    "__version__",
    "RbnfEngine",
    "RulesetName",
]
