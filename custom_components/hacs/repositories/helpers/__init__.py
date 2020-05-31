# pylint: disable=missing-class-docstring,missing-module-docstring,missing-function-docstring,no-member
from custom_components.hacs.repositories.helpers.methods import RepositoryHelperMethods
from custom_components.hacs.repositories.helpers.properties import (
    RepositoryHelperProperties,
)


class RepositoryHelpers(
    RepositoryHelperMethods, RepositoryHelperProperties,
):
    pass
