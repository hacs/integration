from collections.abc import Generator
import os
from pathlib import Path

from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.repositories.plugin import HacsPluginRepository

from tests.common import (
    CategoryTestData,
    WSClient,
    category_test_data_parametrized,
    get_hacs,
)
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
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


    match repo.data.category:
        case "theme" | "python_script":
            repo.data.file_name = category_test_data["files"][0]
        case "plugin":
            repo.data.file_name = category_test_data["files"][0]
            assert isinstance(repo, HacsPluginRepository)
            resources = repo._get_resource_handler()
            assert resources.async_items() == []

            await repo.update_dashboard_resources()
            repo.update_filenames()

            first_resource = resources.async_items()[0]
            assert first_resource["url"] == repo.generate_dashboard_resource_url()


    # workaround for local path bug in tests
    repo.content.path.local = repo.localpath

    for file in category_test_data["files"]:
        Path(repo.localpath, Path(file).parent).mkdir(parents=True, exist_ok=True)
        Path(repo.localpath, file).touch()

    await snapshots.assert_hacs_data(
        hacs, f"{category_test_data['repository']}/test_remove_repository_pre.json",
    )

    response = await ws_client.send_and_receive_json(
        "hacs/repository/remove", {"repository": repo.data.id},
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
        hacs, f"{category_test_data['repository']}/test_remove_repository_post.json",
    )
