import json

import pytest
from pytest_snapshot.plugin import Snapshot

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsCategory
from custom_components.hacs.utils.data import HacsData

from tests.common import client_session_proxy


@pytest.mark.parametrize(
    "repository_full_name,category",
    (
        ("hacs-test-org/integration-basic", HacsCategory.INTEGRATION),
        ("hacs-test-org/template-basic", HacsCategory.TEMPLATE),
    ),
)
@pytest.mark.asyncio
async def test_register_repository(
    hacs: HacsBase, repository_full_name: str, category: HacsCategory, snapshot: Snapshot
):
    snapshot.snapshot_dir = "tests/snapshots"
    data = HacsData(hacs)
    hacs.session = await client_session_proxy(hacs.hass)

    full_name = f"hacs-test-org/{category.value}"

    assert hacs.repositories.get_by_full_name(repository_full_name) is None
    await hacs.async_register_repository(repository_full_name, category)
    repo = hacs.repositories.get_by_full_name(repository_full_name)

    assert repo is not None

    repo.data.last_fetched = None
    data.async_store_experimental_repository_data(repo)
    snapshot.assert_match(
        json.dumps(data.content, indent=4),
        f"{repository_full_name}/test_register_repository.json",
    )
