# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from .exsist_on_local_fs import RepositoryMethodExsistOnLocalFS
from .reinstall_if_needed import RepositoryMethodReinstallIfNeeded
from .installation import (
    RepositoryMethodPreInstall,
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
)


class RepositoryHelperMethods(
    RepositoryMethodExsistOnLocalFS,
    RepositoryMethodReinstallIfNeeded,
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
    RepositoryMethodPreInstall,
):
    pass
