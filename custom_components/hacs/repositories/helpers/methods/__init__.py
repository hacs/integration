# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from .exsist_on_local_fs import RepositoryMethodExsistOnLocalFS
from .reinstall_if_needed import RepositoryMethodReinstallIfNeeded
from .install import RepositoryMethodInstall


class RepositoryHelperMethods(
    RepositoryMethodExsistOnLocalFS,
    RepositoryMethodReinstallIfNeeded,
    RepositoryMethodInstall,
):
    pass
