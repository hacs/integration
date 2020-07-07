import pytest

from custom_components.hacs.helpers.functions.path_exsist import async_path_exsist
from tests.dummy_repository import dummy_repository_base


@pytest.mark.asyncio
async def test_exsist_on_local_fs(tmpdir):
    repository = dummy_repository_base()
    repository.content.path.local = tmpdir
    assert await async_path_exsist(repository.content.path.local)
