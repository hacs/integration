"""Custom logger for HACS."""
import os
import logging


class HacsLogger:
    def __init__(self, name=None) -> None:
        self.name = f"custom_components.hacs{'.' + name if name else ''}"


def getLogger(name=None):
    if "GITHUB_ACTION" in os.environ or "DEVCONTAINER" in os.environ:
        logging.basicConfig(
            format="::%(levelname)s:: %(message)s", level="DEBUG",
        )

    return logging.getLogger(
        f"custom_components.hacs{'.' + name if name is not None else ''}"
    )

