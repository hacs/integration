# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from .installation import (
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
    RepositoryMethodPreInstall,
)
from .registration import (
    RepositoryMethodPostRegistration,
    RepositoryMethodPreRegistration,
    RepositoryMethodRegistration,
)
from .reinstall_if_needed import (
    RepositoryMethodReinstallIfNeeded,
)


class RepositoryHelperMethods(
    RepositoryMethodReinstallIfNeeded,
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
    RepositoryMethodPreInstall,
    RepositoryMethodPreRegistration,
    RepositoryMethodRegistration,
    RepositoryMethodPostRegistration,
):
    """Collection of repository methods that are nested to all repositories."""


class HacsHelperMethods:
    """Helper class for HACS methods"""
