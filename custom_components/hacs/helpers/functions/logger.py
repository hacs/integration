"""Custom logger for HACS."""
import logging


def getLogger(name=None):
    if name is not None:
        return logging.getLogger(f"custom_components.hacs.{name}")
    return logging.getLogger("custom_components.hacs")
