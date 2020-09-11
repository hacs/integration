"""Custom logger for HACS."""
import logging
import os


def getLogger(name=None):
    if name is not None:
        name = name.replace("/", ".")

    if "GITHUB_ACTION" in os.environ:
        logging.basicConfig(
            format="::%(levelname)s:: %(message)s",
            level="DEBUG",
        )

    return logging.getLogger(
        f"custom_components.hacs{'.' + name if name is not None else ''}"
    )
