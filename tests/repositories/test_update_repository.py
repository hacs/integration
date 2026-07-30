from collections.abc import Generator
import json
from pathlib import Path
import re
from unittest.mock import patch

from homeassistant.core import HomeAssistant, HomeAssistantError
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
import pytest

from custom_components.hacs.const import DOMAIN
from custom_components.hacs.exceptions import HacsException

from tests.common import (
    CategoryTestData,
    MockedResponse,
    ResponseMocker,
    WSClient,
    category_test_data_parametrized,
    get_hacs,
)
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_update_repository_entity(
    hass: HomeAssistant,
    setup_integration: Generator,
    category_test_data: CategoryTestData,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(category_test_data["repository"])

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = category_test_data["version_base"]

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)

    er = async_get_entity_registry(hacs.hass)

    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    await hass.services.async_call(
        "update",
        "install",
        service_data={"entity_id": entity_id,
                      "version": category_test_data["version_update"]},
        blocking=True,
    )
    repo = hacs.repositories.get_by_full_name(category_test_data["repository"])
    assert repo.data.installed_version == category_test_data["version_update"]

    await snapshots.assert_hacs_data(
        hacs,
        f"{category_test_data['repository']
           }/test_update_repository_entity.json",
    )


@pytest.mark.parametrize("category_test_data", category_test_data_parametrized())
async def test_update_repository_websocket(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
    category_test_data: CategoryTestData,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(category_test_data["repository"])

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = category_test_data["version_base"]

    response = await ws_client.send_and_receive_json(
        "hacs/repository/download",
        {"repository": repo.data.id,
            "version": category_test_data["version_update"]},
    )
    assert response["success"] == True
    assert repo.data.installed_version == category_test_data["version_update"]

    await snapshots.assert_hacs_data(
        hacs,
        f"{category_test_data['repository']
           }/test_update_repository_websocket.json",
    )


async def test_update_repository_entity_no_manifest(
    hass: HomeAssistant,
    setup_integration: Generator,
    snapshots: SnapshotFixture,
    response_mocker: ResponseMocker,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = "1.0.0"

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    response_mocker.add(
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/3.0.0/hacs.json",
        MockedResponse(status=404),
    )

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)

    er = async_get_entity_registry(hacs.hass)

    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    with pytest.raises(
        HomeAssistantError,
        match=re.escape(
            "The version 3.0.0 for this integration can not be used with HACS."),
    ):
        await hass.services.async_call(
            "update",
            "install",
            service_data={"entity_id": entity_id, "version": "3.0.0"},
            blocking=True,
        )


async def test_update_repository_entity_old_core_version(
    hass: HomeAssistant,
    setup_integration: Generator,
    snapshots: SnapshotFixture,
    response_mocker: ResponseMocker,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = "1.0.0"

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    response_mocker.add(
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/3.0.0/hacs.json",
        MockedResponse(content=json.dumps({"homeassistant": "9999.99.99"})),
    )

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)

    er = async_get_entity_registry(hacs.hass)

    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    with pytest.raises(
        HomeAssistantError,
        match=re.escape(
            "This version requires Home Assistant 9999.99.99 or newer."),
    ):
        await hass.services.async_call(
            "update",
            "install",
            service_data={"entity_id": entity_id, "version": "3.0.0"},
            blocking=True,
        )


async def test_update_repository_entity_old_hacs_version(
    hass: HomeAssistant,
    setup_integration: Generator,
    snapshots: SnapshotFixture,
    response_mocker: ResponseMocker,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = "1.0.0"

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    response_mocker.add(
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/3.0.0/hacs.json",
        MockedResponse(content=json.dumps({"hacs": "9999.99.99"})),
    )

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)

    er = async_get_entity_registry(hacs.hass)

    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    with pytest.raises(HomeAssistantError, match=re.escape("This version requires HACS 9999.99.99 or newer.")):
        await hass.services.async_call(
            "update",
            "install",
            service_data={"entity_id": entity_id, "version": "3.0.0"},
            blocking=True,
        )


async def test_update_repository_entity_download_failure(
    hass: HomeAssistant,
    setup_integration: Generator,
    snapshots: SnapshotFixture,
    response_mocker: ResponseMocker,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = "1.0.0"

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    response_mocker.add(
        "https://github.com/hacs-test-org/integration-basic/archive/refs/tags/2.0.0.zip",
        MockedResponse(status=503),
    )
    response_mocker.add(
        "https://github.com/hacs-test-org/integration-basic/archive/refs/heads/2.0.0.zip",
        MockedResponse(status=503),
    )

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)

    er = async_get_entity_registry(hacs.hass)

    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    with pytest.raises(
        HomeAssistantError,
        match=re.escape(
            "Downloading hacs-test-org/integration-basic with version 2.0.0 failed with (Could not download, see log for details)",
        ),
    ):
        await hass.services.async_call(
            "update",
            "install",
            service_data={"entity_id": entity_id, "version": "2.0.0"},
            blocking=True,
        )


async def test_update_repository_entity_download_exception_restores_backup(
    hass: HomeAssistant,
    setup_integration: Generator,
):
    """Ensure the old install is restored when the download step raises."""
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = "1.0.0"

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    installed_file = Path(repo.localpath) / "__init__.py"
    installed_file.parent.mkdir(parents=True, exist_ok=True)
    installed_file.write_text("old install")

    er = async_get_entity_registry(hacs.hass)
    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    with patch(
        "custom_components.hacs.repositories.base.HacsRepository.download_content",
        side_effect=HacsException("No content to download"),
    ), pytest.raises(
        HomeAssistantError,
        match=re.escape(
            "Downloading hacs-test-org/integration-basic with version 2.0.0 failed with (No content to download)",
        ),
    ):
        await hass.services.async_call(
            "update",
            "install",
            service_data={"entity_id": entity_id, "version": "2.0.0"},
            blocking=True,
        )

    assert installed_file.exists()
    assert installed_file.read_text() == "old install"


async def test_update_repository_entity_download_failure_keeps_persistent_directory(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
):
    """Ensure the persistent directory survives a failed download."""
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = "1.0.0"

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    # Set a persistent directory on the manifest, and 404 the hacs.json
    # fetch so the update flow keeps the manifest set here.
    repo.repository_manifest.persistent_directory = "userfiles"
    response_mocker.add(
        "https://api.github.com/repos/hacs-test-org/integration-basic/contents/hacs.json",
        MockedResponse(status=404, keep=True),
    )

    response_mocker.add(
        "https://github.com/hacs-test-org/integration-basic/archive/refs/tags/2.0.0.zip",
        MockedResponse(status=503),
    )
    response_mocker.add(
        "https://github.com/hacs-test-org/integration-basic/archive/refs/heads/2.0.0.zip",
        MockedResponse(status=503),
    )

    persistent_file = Path(repo.localpath) / "userfiles" / "data.txt"
    persistent_file.parent.mkdir(parents=True, exist_ok=True)
    persistent_file.write_text("Important user data")

    er = async_get_entity_registry(hacs.hass)
    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    with pytest.raises(
        HomeAssistantError,
        match=re.escape(
            "Downloading hacs-test-org/integration-basic with version 2.0.0 failed with (Could not download, see log for details)",
        ),
    ):
        await hass.services.async_call(
            "update",
            "install",
            service_data={"entity_id": entity_id, "version": "2.0.0"},
            blocking=True,
        )

    assert persistent_file.exists()
    assert persistent_file.read_text() == "Important user data"


async def test_update_repository_entity_same_provided_version(
    hass: HomeAssistant, setup_integration: Generator
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = "2.0.0"

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)

    er = async_get_entity_registry(hacs.hass)

    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    with pytest.raises(
        HomeAssistantError,
        match=re.escape(
            "Version 2.0.0 of hacs-test-org/integration-basic is already downloaded",
        ),
    ):
        await hass.services.async_call(
            "update",
            "install",
            service_data={"entity_id": entity_id, "version": "2.0.0"},
            blocking=True,
        )


async def test_update_repository_entity_no_update(
    hass: HomeAssistant,
    setup_integration: Generator,
):
    hacs = get_hacs(hass)
    repo = hacs.repositories.get_by_full_name(
        "hacs-test-org/integration-basic")

    assert repo is not None

    repo.data.installed = True
    repo.data.installed_version = "1.0.0"

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)
    await hass.async_block_till_done()

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)

    er = async_get_entity_registry(hacs.hass)

    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    with pytest.raises(
        HomeAssistantError,
        match=re.escape(
            "No update available for update.basic_integration_update",
        ),
    ):
        await hass.services.async_call(
            "update",
            "install",
            service_data={"entity_id": entity_id},
            blocking=True,
        )
