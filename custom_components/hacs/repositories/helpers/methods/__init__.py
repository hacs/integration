# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from .exsist_on_local_fs import RepositoryMethodExsistOnLocalFS
from .reinstall_if_needed import RepositoryMethodReinstallIfNeeded
from .install import RepositoryMethodInstall
from .pre_install import RepositoryMethodPreInstall
from .post_install import RepositoryMethodPostInstall


class RepositoryHelperMethods(
    RepositoryMethodExsistOnLocalFS,
    RepositoryMethodReinstallIfNeeded,
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
    RepositoryMethodPreInstall,
):
    pass
