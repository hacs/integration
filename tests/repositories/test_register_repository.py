from collections.abc import Generator

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
import pytest

from custom_components.hacs.enums import HacsCategory, HacsDispatchEvent

from tests.common import WSClient, get_hacs, recursive_remove_key, safe_json_dumps
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "repository_full_name,category",
    (
        ("hacs-test-org/integration-basic-custom", HacsCategory.INTEGRATION),
        ("hacs-test-org/plugin-custom-dist", HacsCategory.PLUGIN),
    ),
)
async def test_register_repository(
    hass: HomeAssistant,
    setup_integration: Generator,
    repository_full_name: str,
    category: HacsCategory,
    snapshots: SnapshotFixture,
    ws_client: WSClient,
):
    hacs = get_hacs(hass)

    assert hacs.repositories.get_by_full_name(repository_full_name) is None

    response = await ws_client.send_and_receive_json(
        "hacs/repositories/add", {"repository": repository_full_name, "category": category.value},
    )
    assert response["success"] == True
    repo = hacs.repositories.get_by_full_name(repository_full_name)
    assert repo is not None

    response = await ws_client.send_and_receive_json(
        "hacs/repository/info", {"repository_id": repo.data.id},
    )
    assert response["success"] == True

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(response["result"], ("last_updated", "local_path"))),
        f"{repository_full_name}/test_register_repository.json",
    )


@pytest.mark.parametrize(
    "repository_full_name,result",
    (
        (
            "home-assistant/core",
            "You can not add homeassistant/core, to use core integrations check the Home Assistant documentation for how to add them.",
        ),
        (
            "home-assistant/addons",
            "The repository does not seem to be a integration, but an add-on repository. HACS does not manage add-ons.",
        ),
        (
            "hassio-addons/example",
            "The repository does not seem to be a integration, but an add-on repository. HACS does not manage add-ons.",
        ),
        (
            "hacs-test-org/addon-basic",
            "The repository does not seem to be a integration, but an add-on repository. HACS does not manage add-ons.",
        ),
        (
            "hacs-test-org/integration-invalid",
            "<Integration hacs-test-org/integration-invalid> Repository structure for main is not compliant",
        ),
    ),
)
async def test_register_repository_failures(
    hass: HomeAssistant,
    setup_integration: Generator,
    repository_full_name: str,
    result: str,
    ws_client: WSClient,
):
    messages = []

    async_dispatcher_connect(
        hass,
        HacsDispatchEvent.ERROR,
        lambda message: messages.append(message),
    )
    hacs = get_hacs(hass)
    assert hacs.repositories.get_by_full_name(repository_full_name) is None

    response = await ws_client.send_and_receive_json(
        "hacs/repositories/add",
        {"repository": repository_full_name, "category": HacsCategory.INTEGRATION},
    )
    await hass.async_block_till_done()
    assert response["success"] == True
    repo = hacs.repositories.get_by_full_name(repository_full_name)
    assert repo is None
    assert response["result"] == {}
    assert len(messages) == 1
    assert messages[0]["action"] == "add_repository"
    assert messages[0]["message"] == result
