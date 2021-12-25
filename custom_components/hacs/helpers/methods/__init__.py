# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from custom_components.hacs.helpers.methods.installation import (
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
    RepositoryMethodPreInstall,
)


class RepositoryHelperMethods(
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
    RepositoryMethodPreInstall,
):
    """Collection of repository methods that are nested to all repositories."""


class HacsHelperMethods:
    """Helper class for HACS methods"""
