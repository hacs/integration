"""Collection of repository methods that are nested to all repositories."""
from .exsist_on_local_fs import RepositoryMethodExsistOnLocalFS
from .reinstall_if_needed import RepositoryMethodReinstallIfNeeded
from .installation import (
    RepositoryMethodPreInstall,
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
)
from .registration import (
    RepositoryMethodPreRegistration,
    RepositoryMethodRegistration,
    RepositoryMethodPostRegistration,
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
