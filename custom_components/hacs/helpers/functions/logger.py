"""Custom logger for HACS."""
import logging

from custom_components.hacs.share import DEVCONTAINER, GITHUB_ACTION


def getLogger(name=None):
    if GITHUB_ACTION:
        logging.basicConfig(
            format="::%(levelname)s:: %(message)s", level="DEBUG",
        )
    elif DEVCONTAINER:
        import colorlog

        colorlog.basicConfig(
            level="DEBUG",
            format=f"%(log_color)s[%(levelname)s - %(name)s] - %(message)s%(reset)s",
        )
        return colorlog.getLogger(name)

    return logging.getLogger(
        f"custom_components.hacs{'.' + name if name is not None else ''}"
    )
