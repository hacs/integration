import pytest
from tests.dummy_repository import dummy_repository_base


@pytest.mark.asyncio
async def test_exsist_on_local_fs(tmpdir):
    repository = dummy_repository_base()
    repository.content.path.local = tmpdir
    assert await repository.async_exsist_on_local_fs()
