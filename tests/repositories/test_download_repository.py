from glob import iglob
import json
import os
from unittest.mock import ANY

import pytest
from pytest_snapshot.plugin import Snapshot

from custom_components.hacs.base import HacsBase
from custom_components.hacs.enums import HacsCategory
from custom_components.hacs.utils.data import HacsData

from tests.common import client_session_proxy


@pytest.mark.parametrize(
    "category",
    ((HacsCategory.INTEGRATION), (HacsCategory.TEMPLATE)),
)
@pytest.mark.asyncio
async def test_download_repository(hacs: HacsBase, category: HacsCategory, snapshot: Snapshot):
    snapshot.snapshot_dir = "tests/snapshots"
    data = HacsData(hacs)
    hacs.session = await client_session_proxy(hacs.hass)
    full_name = f"octocat/{category.value}"

    await hacs.async_register_repository(full_name, category)
    repo = hacs.repositories.get_by_full_name(full_name)
    assert repo is not None
    assert repo.data.installed is False

    assert not os.path.isdir(repo.localpath)

    await repo.async_install()

    assert repo.data.installed is True
    assert os.path.isdir(repo.localpath)
    downloaded = [
        f.replace(f"{hacs.core.config_path}", "/config")
        for f in iglob(f"{hacs.core.config_path}/**", recursive=True)
        if os.path.isfile(f)
    ]
    assert len(downloaded) != 0

    repo.data.last_fetched = None
    data.async_store_experimental_repository_data(repo)
    snapshot.assert_match(
        json.dumps({"files": downloaded, "content": data.content}, indent=4),
        f"{category.value}_test_download_repository.json",
    )
