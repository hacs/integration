# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from .pending_update import RepositoryPropertyPendingUpdate
from .custom import RepositoryPropertyCustom
from .can_be_installed import RepositoryPropertyCanBeInstalled


class RepositoryHelperProperties(
    RepositoryPropertyPendingUpdate,
    RepositoryPropertyCustom,
    RepositoryPropertyCanBeInstalled,
):
    pass
