"""Bind HACS to classes."""
from ..share import get_hacs


def bind_hacs(cls):
    cls.__hacs = get_hacs()
    return cls