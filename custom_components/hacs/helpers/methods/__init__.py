# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member

from custom_components.hacs.helpers.methods.exsist_on_local_fs import (
    RepositoryMethodExsistOnLocalFS,
)
from custom_components.hacs.helpers.methods.get_list_from_default import (
    GetListFromDefault,
)
from custom_components.hacs.helpers.methods.installation import (
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
    RepositoryMethodPreInstall,
)
from custom_components.hacs.helpers.methods.registration import (
    RepositoryMethodPostRegistration,
    RepositoryMethodPreRegistration,
    RepositoryMethodRegistration,
)
from custom_components.hacs.helpers.methods.reinstall_if_needed import (
    RepositoryMethodReinstallIfNeeded,
)


class RepositoryHelperMethods(
    RepositoryMethodExsistOnLocalFS,
    RepositoryMethodReinstallIfNeeded,
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
    RepositoryMethodPreInstall,
    RepositoryMethodPreRegistration,
    RepositoryMethodRegistration,
    RepositoryMethodPostRegistration,
):
    """Collection of repository methods that are nested to all repositories."""


class HacsHelperMethods(GetListFromDefault):
    """Helper class for HACS methods"""
