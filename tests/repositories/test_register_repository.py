import json
import pytest
from pytest_snapshot.plugin import Snapshot
from unittest.mock import ANY

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsCategory
from custom_components.hacs.utils.data import HacsData

from tests.common import client_session_proxy


@pytest.mark.parametrize(
    "category",
    (HacsCategory.INTEGRATION, HacsCategory.TEMPLATE),
)
@pytest.mark.asyncio
async def test_register_repository(hacs: HacsBase, category: HacsCategory, snapshot: Snapshot):
    snapshot.snapshot_dir = "tests/snapshots"
    data = HacsData(hacs)
    hacs.session = await client_session_proxy(hacs.hass)

    full_name = f"octocat/{category.value}"

    assert hacs.repositories.get_by_full_name(full_name) is None
    await hacs.async_register_repository(full_name, category)
    repo = hacs.repositories.get_by_full_name(full_name)

    assert repo is not None

    repo.data.last_fetched = None
    data.async_store_experimental_repository_data(repo)
    snapshot.assert_match(
        json.dumps(
            data.content, indent=4
        ),
        f"{category.value}_test_register_repository.json",
    )
