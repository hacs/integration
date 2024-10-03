"""Logger related helpers."""

import logging
from typing import cast

import coloredlogs
from coloredlogs import ColoredFormatter


class MatterFormatter(ColoredFormatter):  # type: ignore[misc]
    """Custom formatter for Matter project."""

    def __init__(
        self,
        fmt: str,
        node_fmt: str,
        datefmt: str,
        style: str = coloredlogs.DEFAULT_FORMAT_STYLE,
        level_styles: dict | None = None,
        field_styles: dict | None = None,
    ):
        """Initialize the Matter specific log formatter."""
        super().__init__(fmt, datefmt, style, level_styles, field_styles)
        self._node_style = logging.PercentStyle(self.colorize_format(node_fmt, style))

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record."""
        original_style = self._style  # type: ignore[has-type]
        if hasattr(record, "node"):
            self._style = self._node_style
        result = super().format(record)
        self._style = original_style
        return cast(str, result)


class MatterNodeFilter(logging.Filter):
    """Filter for Matter project to filter by node."""

    def __init__(self, node: set[int], name: str = ""):
        """Initialize the filter."""
        super().__init__(name)
        self.node = node

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter the log record."""
        if not hasattr(record, "node"):
            return True

        # Always display warnings and above
        if record.levelno >= logging.WARNING:
            return True
        return record.node in self.node
