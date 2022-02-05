# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsCategory
from custom_components.hacs.repositories.base import HacsRepository


@pytest.mark.asyncio
async def test_update_all_repositories(hacs: HacsBase, repository: HacsRepository):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_all_repositories")

    repository.data.category = HacsCategory.INTEGRATION
    hacs.repositories.register(repository)
    hacs.enable_hacs_category(HacsCategory.INTEGRATION)

    assert task

    assert hacs.queue.pending_tasks == 0
    await task.execute_task()
    assert hacs.queue.pending_tasks == 1
