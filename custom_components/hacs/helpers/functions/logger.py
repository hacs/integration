"""Custom logger for HACS."""
import logging

from custom_components.hacs.variables import GITHUB_ACTION


def getLogger(name=None):
    if name is not None:
        name = name.replace("/", ".")

    if GITHUB_ACTION:
        logging.basicConfig(
            format="::%(levelname)s:: %(message)s", level="DEBUG",
        )

    return logging.getLogger(
        f"custom_components.hacs{'.' + name if name is not None else ''}"
    )
