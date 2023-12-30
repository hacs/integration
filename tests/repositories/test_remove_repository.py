import os
from pathlib import Path
from typing import Generator

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.enums import HacsCategory

from tests.common import (
    CategoryTestData,
    WSClient,
    category_test_data_parametrized,
    get_hacs,
)
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "category_test_data",
    category_test_data_parametrized(
        skip_categories=[HacsCategory.PYTHON_SCRIPT],
        skip_reason="bug in cleanup, using repo name instead of file name.",
    ),
)
async def test_remove_repository(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
    category_test_data: CategoryTestData,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)

    repo = hacs.repositories.get_by_full_name(category_test_data["repository"])
    assert repo is not None
    assert repo.data.installed is False
    repo.data.installed = True

    assert len(hacs.repositories.list_downloaded) == 2

    if repo.data.category in ("theme", "python_script"):
        repo.data.file_name = category_test_data["files"][0]

    # workaround for local path bug in tests
    repo.content.path.local = repo.localpath

    Path(repo.localpath).mkdir(parents=True, exist_ok=True)
    for file in category_test_data["files"]:
        Path(repo.localpath, file).touch()

    await snapshots.assert_hacs_data(
        hacs, f"{category_test_data['repository']}/test_remove_repository_pre.json"
    )

    response = await ws_client.send_and_receive_json(
        "hacs/repository/remove", {"repository": repo.data.id}
    )
    assert response["success"] == True

    assert len(hacs.repositories.list_downloaded) == 1

    assert repo.data.installed is False
    if repo.content.single:
        for file in category_test_data["files"]:
            assert not os.path.exists(Path(repo.content.path.local, file))
    else:
        assert not os.path.exists(repo.localpath)

    await snapshots.assert_hacs_data(
        hacs, f"{category_test_data['repository']}/test_remove_repository_post.json"
    )
