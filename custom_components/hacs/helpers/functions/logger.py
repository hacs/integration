"""Custom logger for HACS."""
import logging
import os

_HACSLogger = logging.getLogger("custom_components.hacs")


class HACSLoggerAdapter(logging.LoggerAdapter):
    """Augment log messages with a name."""

    def process(self, msg, kwargs):
        """Augment log messages with a name."""
        return f'[{self.extra["name"]}] {msg}', kwargs


def getLogger(name=None):
    if name is not None:
        name = name.replace("/", ".")

    if "GITHUB_ACTION" in os.environ:
        logging.basicConfig(
            format="::%(levelname)s:: %(message)s",
            level="DEBUG",
        )

    if name is None:
        return _HACSLogger

    return HACSLoggerAdapter(_HACSLogger, {"name": name})
