# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from custom_components.hacs.helpers.properties.can_be_installed import (
    RepositoryPropertyCanBeInstalled,
)
from custom_components.hacs.helpers.properties.custom import RepositoryPropertyCustom
from custom_components.hacs.helpers.properties.pending_update import (
    RepositoryPropertyPendingUpdate,
)


class RepositoryHelperProperties(
    RepositoryPropertyPendingUpdate,
    RepositoryPropertyCustom,
    RepositoryPropertyCanBeInstalled,
):
    pass
