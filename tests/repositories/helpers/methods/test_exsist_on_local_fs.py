import pytest

from custom_components.hacs.helpers.functions.path_exsist import async_path_exsist


@pytest.mark.asyncio
async def test_exsist_on_local_fs(repository, tmpdir):
    repository.content.path.local = tmpdir
    assert await async_path_exsist(repository.content.path.local)
