# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from custom_components.hacs.helpers.methods import (
    HacsHelperMethods,
    RepositoryHelperMethods,
)
from custom_components.hacs.helpers.properties import RepositoryHelperProperties


class RepositoryHelpers(
    RepositoryHelperMethods,
    RepositoryHelperProperties,
):
    """Helper class for repositories"""


class HacsHelpers(HacsHelperMethods):
    """Helper class for HACS"""
