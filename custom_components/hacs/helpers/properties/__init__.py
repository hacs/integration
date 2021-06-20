# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from .can_be_installed import (
    RepositoryPropertyCanBeInstalled,
)
from .custom import RepositoryPropertyCustom
from .pending_update import (
    RepositoryPropertyPendingUpdate,
)


class RepositoryHelperProperties(
    RepositoryPropertyPendingUpdate,
    RepositoryPropertyCustom,
    RepositoryPropertyCanBeInstalled,
):
    pass
