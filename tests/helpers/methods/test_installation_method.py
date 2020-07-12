from abc import ABC
import pytest

from custom_components.hacs.share import get_hacs
from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.helpers.classes.repositorydata import RepositoryData
from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.helpers.classes.validate import Validate
from custom_components.hacs.helpers.methods import (
    RepositoryMethodInstall,
    RepositoryMethodPostInstall,
    RepositoryMethodPreInstall,
)

from tests.common import TOKEN


class MockPath:
    local = None


class MockContent:
    path = MockPath()


class MockRepo(
    RepositoryMethodInstall, RepositoryMethodPreInstall, RepositoryMethodPostInstall
):
    logger = getLogger()
    content = MockContent()
    validate = Validate()
    can_install = False
    data = RepositoryData()
    tree = []
    hacs = get_hacs()

    async def update_repository(self):
        pass


@pytest.mark.asyncio
async def test_installation_method():
    hacs = get_hacs()
    hacs.configuration = Configuration()
    hacs.configuration.token = TOKEN
    repo = MockRepo()

    with pytest.raises(HacsException):
        await repo.async_install()
    repo.content.path.local = ""

    with pytest.raises(HacsException):
        await repo.async_install()
    repo.can_install = True

    await repo._async_post_install()
