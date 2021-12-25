# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from custom_components.hacs.helpers.methods import (
    HacsHelperMethods,
    RepositoryHelperMethods,
)


class RepositoryHelpers(
    RepositoryHelperMethods,
):
    """Helper class for repositories"""


class HacsHelpers(HacsHelperMethods):
    """Helper class for HACS"""
