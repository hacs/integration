"""Test HACS repository lists websocket commands."""

from collections.abc import Generator

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from custom_components.hacs.enums import HacsDispatchEvent
from custom_components.hacs.utils.store import async_load_from_store

from tests.common import WSClient, get_hacs


async def test_lists_lifecycle(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
) -> None:
    """Test creating, renaming and deleting lists."""
    messages: list[dict] = []
    unsub = async_dispatcher_connect(hass, HacsDispatchEvent.LISTS, messages.append)
    try:
        response = await ws_client.send_and_receive_json("hacs/lists/list", {})
        assert response["success"] is True
        assert len(response["result"]) == 1
        assert response["result"][0] == {
            "id": "favourite",
            "name": "Favourite",
            "builtin": True,
            "repositories": [],
        }

        response = await ws_client.send_and_receive_json(
            "hacs/lists/create",
            {"name": "My Integrations"},
        )
        assert response["success"] is True
        created = next(
            item for item in response["result"] if item["name"] == "My Integrations"
        )
        assert created["builtin"] is False
        assert messages[-1]["action"] == "create"

        response = await ws_client.send_and_receive_json(
            "hacs/lists/rename",
            {"list_id": created["id"], "name": "My Components"},
        )
        assert response["success"] is True
        renamed = next(
            item for item in response["result"] if item["id"] == created["id"]
        )
        assert renamed["name"] == "My Components"
        assert messages[-1]["action"] == "rename"

        response = await ws_client.send_and_receive_json(
            "hacs/lists/delete",
            {"list_id": created["id"]},
        )
        assert response["success"] is True
        assert response["result"] == [
            {
                "id": "favourite",
                "name": "Favourite",
                "builtin": True,
                "repositories": [],
            }
        ]
        assert messages[-1]["action"] == "delete"

        stored = await async_load_from_store(hass, "lists")
        assert set(stored["lists"]) == {"favourite"}
    finally:
        unsub()


async def test_lists_repository_membership(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
) -> None:
    """Test repository membership in multiple lists."""
    hacs = get_hacs(hass)
    repository = hacs.repositories.get_by_full_name("hacs-test-org/integration-basic")
    assert repository is not None

    create_response = await ws_client.send_and_receive_json(
        "hacs/lists/create",
        {"name": "Components"},
    )
    assert create_response["success"] is True
    components = next(
        item for item in create_response["result"] if item["name"] == "Components"
    )

    response = await ws_client.send_and_receive_json(
        "hacs/lists/set_repository",
        {
            "repository": str(repository.data.id),
            "lists": ["favourite", components["id"]],
        },
    )
    assert response["success"] is True

    favourite = next(item for item in response["result"] if item["id"] == "favourite")
    selected = next(item for item in response["result"] if item["id"] == components["id"])
    expected_repository = {
        "id": str(repository.data.id),
        "full_name": repository.data.full_name,
    }
    assert favourite["repositories"] == [expected_repository]
    assert selected["repositories"] == [expected_repository]

    # Updating membership replaces the repository's previous list assignments.
    response = await ws_client.send_and_receive_json(
        "hacs/lists/set_repository",
        {
            "repository": str(repository.data.id),
            "lists": [components["id"]],
        },
    )
    assert response["success"] is True
    favourite = next(item for item in response["result"] if item["id"] == "favourite")
    selected = next(item for item in response["result"] if item["id"] == components["id"])
    assert favourite["repositories"] == []
    assert selected["repositories"] == [expected_repository]

    stored = await async_load_from_store(hass, "lists")
    assert stored["lists"][components["id"]]["repositories"] == {
        str(repository.data.id): repository.data.full_name,
    }

    list_response = await ws_client.send_and_receive_json("hacs/lists/list", {})
    assert list_response["success"] is True
    selected = next(
        item for item in list_response["result"] if item["id"] == components["id"]
    )
    assert selected["repositories"] == [expected_repository]


async def test_lists_validation(
    hass: HomeAssistant,
    setup_integration: Generator,
    ws_client: WSClient,
) -> None:
    """Test invalid list operations are rejected."""
    hacs = get_hacs(hass)
    repository = hacs.repositories.get_by_full_name("hacs-test-org/integration-basic")
    assert repository is not None

    response = await ws_client.send_and_receive_json(
        "hacs/lists/create",
        {"name": "Components"},
    )
    assert response["success"] is True
    components = next(
        item for item in response["result"] if item["name"] == "Components"
    )

    response = await ws_client.send_and_receive_json(
        "hacs/lists/create",
        {"name": "components"},
    )
    assert response["success"] is False
    assert response["error"]["code"] == "list_exists"

    response = await ws_client.send_and_receive_json(
        "hacs/lists/create",
        {"name": "Favourite"},
    )
    assert response["success"] is False
    assert response["error"]["code"] == "list_exists"

    rename_response = await ws_client.send_and_receive_json(
        "hacs/lists/rename",
        {"list_id": components["id"], "name": "Favourite"},
    )
    assert rename_response["success"] is False
    assert rename_response["error"]["code"] == "list_exists"

    response = await ws_client.send_and_receive_json(
        "hacs/lists/rename",
        {"list_id": "favourite", "name": "Pinned"},
    )
    assert response["success"] is False
    assert response["error"]["code"] == "builtin_list"

    response = await ws_client.send_and_receive_json(
        "hacs/lists/delete",
        {"list_id": "favourite"},
    )
    assert response["success"] is False
    assert response["error"]["code"] == "builtin_list"

    response = await ws_client.send_and_receive_json(
        "hacs/lists/rename",
        {"list_id": "missing", "name": "Renamed"},
    )
    assert response["success"] is False
    assert response["error"]["code"] == "list_not_found"

    response = await ws_client.send_and_receive_json(
        "hacs/lists/delete",
        {"list_id": "missing"},
    )
    assert response["success"] is False
    assert response["error"]["code"] == "list_not_found"

    response = await ws_client.send_and_receive_json(
        "hacs/lists/set_repository",
        {
            "repository": "missing",
            "lists": [components["id"]],
        },
    )
    assert response["success"] is False
    assert response["error"]["code"] == "repository_not_found"

    response = await ws_client.send_and_receive_json(
        "hacs/lists/set_repository",
        {
            "repository": str(repository.data.id),
            "lists": ["missing"],
        },
    )
    assert response["success"] is False
    assert response["error"]["code"] == "list_not_found"

