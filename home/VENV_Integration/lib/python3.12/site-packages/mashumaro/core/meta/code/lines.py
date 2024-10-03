from contextlib import contextmanager
from typing import Generator, List, Optional

__all__ = ["CodeLines"]


class CodeLines:
    def __init__(self) -> None:
        self._lines: List[str] = []
        self._current_indent: str = ""

    def append(self, line: str) -> None:
        self._lines.append(f"{self._current_indent}{line}")

    def extend(self, lines: "CodeLines") -> None:
        self._lines.extend(lines._lines)

    @contextmanager
    def indent(
        self,
        expr: Optional[str] = None,
    ) -> Generator[None, None, None]:
        if expr:
            self.append(expr)
        self._current_indent += " " * 4
        try:
            yield
        finally:
            self._current_indent = self._current_indent[:-4]

    def as_text(self) -> str:
        return "\n".join(self._lines)

    def reset(self) -> None:
        self._lines = []
        self._current_indent = ""

    def branch_off(self) -> "CodeLines":
        branch = CodeLines()
        branch._current_indent = self._current_indent
        return branch
