# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from .methods import (
    HacsHelperMethods,
    RepositoryHelperMethods,
)
from .properties import RepositoryHelperProperties


class RepositoryHelpers(
    RepositoryHelperMethods,
    RepositoryHelperProperties,
):
    """Helper class for repositories"""


class HacsHelpers(HacsHelperMethods):
    """Helper class for HACS"""
