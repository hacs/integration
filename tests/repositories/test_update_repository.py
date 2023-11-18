import json
import pytest
from pytest_snapshot.plugin import Snapshot
from unittest.mock import ANY

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsCategory
from custom_components.hacs.utils.data import HacsData

from tests.common import client_session_proxy, repository_update_entry


@pytest.mark.parametrize(
    "category,from_version,to_version",
    ((HacsCategory.INTEGRATION, "1.0.0", "2.0.0"),(HacsCategory.TEMPLATE, "1.0.0", "2.0.0")),
)
@pytest.mark.asyncio
async def test_update_repository(
    hacs: HacsBase, category: HacsCategory, from_version: str, to_version: str, snapshot: Snapshot
):
    snapshot.snapshot_dir = "tests/snapshots"
    data = HacsData(hacs)
    hacs.session = await client_session_proxy(hacs.hass)
    full_name = f"octocat/{category.value}"

    await hacs.async_register_repository(full_name, category)
    repo = hacs.repositories.get_by_full_name(full_name)
    assert repo is not None
    await repo.async_install(version=from_version)
    assert repo.data.installed is True
    assert repo.data.installed_version == from_version

    entity = repository_update_entry(hacs, repo)

    await entity.async_install(version=to_version, backup=False)
    assert repo.data.installed_version == to_version

    repo.data.last_fetched = None
    data.async_store_experimental_repository_data(repo)
    snapshot.assert_match(
        json.dumps(
            data.content, indent=4
        ),
        f"{category.value}_test_update_repository.json",
    )

