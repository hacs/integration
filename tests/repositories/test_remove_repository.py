import os
from pathlib import Path
from typing import Generator

from homeassistant.core import HomeAssistant
import pytest

from tests.common import WSClient, get_hacs
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "repository_full_name,files",
    (
        ("hacs-test-org/appdaemon-basic", ["__init__.py"]),
        ("hacs-test-org/integration-basic", ["__init__.py", "manifest.json"]),
        ("hacs-test-org/plugin-basic", ["example.js", "example.js.gz"]),
        ("hacs-test-org/template-basic", ["example.jinja"]),
        ("hacs-test-org/theme-basic", ["example.yaml"]),
    ),
)
async def test_remove_repository(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
    repository_full_name: str,
    files: list[str],
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)

    repo = hacs.repositories.get_by_full_name(repository_full_name)
    assert repo is not None
    assert repo.data.installed is False
    repo.data.installed = True

    assert len(hacs.repositories.list_downloaded) == 2

    if repo.data.category == "theme":
        repo.data.file_name = files[0]

    # workaround for local path bug in tests
    repo.content.path.local = repo.localpath

    Path(repo.localpath).mkdir(parents=True, exist_ok=True)
    for file in files:
        Path(repo.localpath, file).touch()

    await snapshots.assert_hacs_data(
        hacs, f"{repository_full_name}/test_remove_repository_pre.json"
    )

    response = await ws_client.send_and_receive_json(
        "hacs/repository/remove", {"repository": repo.data.id}
    )
    assert response["success"] == True

    assert len(hacs.repositories.list_downloaded) == 1

    assert repo.data.installed is False
    if repo.content.single:
        for file in files:
            assert not os.path.exists(Path(repo.content.path.local, file))
    else:
        assert not os.path.exists(repo.localpath)

    await snapshots.assert_hacs_data(
        hacs, f"{repository_full_name}/test_remove_repository_post.json"
    )
