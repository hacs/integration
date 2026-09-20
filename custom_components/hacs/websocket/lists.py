"""Register HACS list websocket commands."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from homeassistant.components import websocket_api
import voluptuous as vol

from ..const import DOMAIN
from ..enums import HacsDispatchEvent
from ..utils.store import async_load_from_store, async_save_to_store

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ..base import HacsBase


STORE_KEY = "lists"
LOCK_KEY = f"{DOMAIN}_lists_lock"

FAVOURITE_ID = "favourite"
FAVOURITE_NAME = "Favourite"

MAX_LIST_NAME_LENGTH = 100


def _get_lock(hass: HomeAssistant) -> asyncio.Lock:
    """Return the lock used for list mutations."""
    lock = hass.data.get(LOCK_KEY)
    if lock is None:
        lock = asyncio.Lock()
        hass.data[LOCK_KEY] = lock
    return lock


def _default_store() -> dict[str, Any]:
    """Return the initial list store."""
    return {
        "lists": {
            FAVOURITE_ID: {
                "name": FAVOURITE_NAME,
                "repositories": {},
            }
        }
    }


async def _load_store(hass: HomeAssistant) -> dict[str, Any]:
    """Load and normalize the list store."""
    data = await async_load_from_store(hass, STORE_KEY)

    if not isinstance(data, dict):
        data = _default_store()

    lists = data.get("lists")

    if not isinstance(lists, dict):
        data = _default_store()
        lists = data["lists"]

    favourite = lists.get(FAVOURITE_ID)

    if not isinstance(favourite, dict):
        lists[FAVOURITE_ID] = {
            "name": FAVOURITE_NAME,
            "repositories": {},
        }
    else:
        favourite["name"] = FAVOURITE_NAME

        if not isinstance(favourite.get("repositories"), dict):
            favourite["repositories"] = {}

    for list_data in lists.values():
        if not isinstance(list_data, dict):
            continue

        if not isinstance(list_data.get("repositories"), dict):
            list_data["repositories"] = {}

    return data


async def _save_store(
    hass: HomeAssistant,
    data: dict[str, Any],
) -> None:
    """Save the list store."""
    await async_save_to_store(hass, STORE_KEY, data)


def _response(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert stored lists to the websocket response."""
    response = []

    for list_id, list_data in data["lists"].items():
        repositories = [
            {
                "id": repository_id,
                "full_name": full_name,
            }
            for repository_id, full_name in list_data["repositories"].items()
        ]

        response.append(
            {
                "id": list_id,
                "name": list_data["name"],
                "builtin": list_id == FAVOURITE_ID,
                "repositories": repositories,
            }
        )

    return response


def _send_result(
    connection: websocket_api.ActiveConnection,
    message_id: int,
    data: dict[str, Any],
) -> None:
    """Send a successful websocket response."""
    connection.send_message(
        websocket_api.result_message(
            message_id,
            _response(data),
        )
    )


def _send_error(
    connection: websocket_api.ActiveConnection,
    message_id: int,
    error_code: str,
    message: str,
) -> None:
    """Send a websocket error response."""
    connection.send_error(
        message_id,
        error_code,
        message,
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/lists/list",
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_lists_list(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Return all HACS lists."""
    async with _get_lock(hass):
        data = await _load_store(hass)

        # Persist the built-in Favourite list if this is the first load.
        await _save_store(hass, data)

    _send_result(
        connection,
        msg["id"],
        data,
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/lists/create",
        vol.Required("name"): vol.All(
            str,
            str.strip,
            vol.Length(
                min=1,
                max=MAX_LIST_NAME_LENGTH,
            ),
        ),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_lists_create(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Create a user list."""
    async with _get_lock(hass):
        data = await _load_store(hass)

        name = msg["name"]
        normalized_name = name.casefold()

        if any(
            list_data["name"].casefold() == normalized_name
            for list_id, list_data in data["lists"].items()
            if list_id != FAVOURITE_ID
        ) or normalized_name == FAVOURITE_NAME.casefold():
            _send_error(
                connection,
                msg["id"],
                "list_exists",
                f"A list named '{name}' already exists.",
            )
            return

        list_id = uuid4().hex

        data["lists"][list_id] = {
            "name": name,
            "repositories": {},
        }

        await _save_store(
            hass,
            data,
        )

    hacs: HacsBase = hass.data.get(DOMAIN)

    hacs.async_dispatch(
        HacsDispatchEvent.LISTS,
        {
            "action": "create",
            "list_id": list_id,
        },
    )

    _send_result(
        connection,
        msg["id"],
        data,
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/lists/rename",
        vol.Required("list_id"): str,
        vol.Required("name"): vol.All(
            str,
            str.strip,
            vol.Length(
                min=1,
                max=MAX_LIST_NAME_LENGTH,
            ),
        ),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_lists_rename(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Rename a user list."""
    async with _get_lock(hass):
        data = await _load_store(hass)

        list_id = msg["list_id"]
        name = msg["name"]

        if list_id == FAVOURITE_ID:
            _send_error(
                connection,
                msg["id"],
                "builtin_list",
                "The Favourite list cannot be renamed.",
            )
            return

        list_data = data["lists"].get(list_id)

        if list_data is None:
            _send_error(
                connection,
                msg["id"],
                "list_not_found",
                f"List with ID ({list_id}) not found.",
            )
            return

        normalized_name = name.casefold()

        if any(
            other_id != list_id
            and other_data["name"].casefold() == normalized_name
            for other_id, other_data in data["lists"].items()
        ) or normalized_name == FAVOURITE_NAME.casefold():
            _send_error(
                connection,
                msg["id"],
                "list_exists",
                f"A list named '{name}' already exists.",
            )
            return

        list_data["name"] = name

        await _save_store(
            hass,
            data,
        )

    hacs: HacsBase = hass.data.get(DOMAIN)

    hacs.async_dispatch(
        HacsDispatchEvent.LISTS,
        {
            "action": "rename",
            "list_id": list_id,
        },
    )

    _send_result(
        connection,
        msg["id"],
        data,
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/lists/delete",
        vol.Required("list_id"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_lists_delete(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Delete a user list."""
    async with _get_lock(hass):
        data = await _load_store(hass)

        list_id = msg["list_id"]

        if list_id == FAVOURITE_ID:
            _send_error(
                connection,
                msg["id"],
                "builtin_list",
                "The Favourite list cannot be deleted.",
            )
            return

        if list_id not in data["lists"]:
            _send_error(
                connection,
                msg["id"],
                "list_not_found",
                f"List with ID ({list_id}) not found.",
            )
            return

        del data["lists"][list_id]

        await _save_store(
            hass,
            data,
        )

    hacs: HacsBase = hass.data.get(DOMAIN)

    hacs.async_dispatch(
        HacsDispatchEvent.LISTS,
        {
            "action": "delete",
            "list_id": list_id,
        },
    )

    _send_result(
        connection,
        msg["id"],
        data,
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/lists/set_repository",
        vol.Required("repository"): str,
        vol.Required("lists"): [str],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_lists_set_repository(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    """Set the lists assigned to a repository."""
    hacs: HacsBase = hass.data.get(DOMAIN)

    repository_id = msg["repository"]
    repository = hacs.repositories.get_by_id(repository_id)

    if repository is None:
        _send_error(
            connection,
            msg["id"],
            "repository_not_found",
            f"Repository with ID ({repository_id}) not found",
        )
        return

    list_ids = set(msg["lists"])

    async with _get_lock(hass):
        data = await _load_store(hass)

        unknown_lists = list_ids - set(data["lists"])

        if unknown_lists:
            _send_error(
                connection,
                msg["id"],
                "list_not_found",
                f"Unknown list IDs: {', '.join(sorted(unknown_lists))}",
            )
            return

        repository_id = str(repository.data.id)
        full_name = repository.data.full_name

        for list_id, list_data in data["lists"].items():
            repositories = list_data["repositories"]

            # Remove the repository from every list first.
            repositories.pop(repository_id, None)

            # Then add it to the selected lists.
            if list_id in list_ids:
                repositories[repository_id] = full_name

        await _save_store(
            hass,
            data,
        )

    hacs.async_dispatch(
        HacsDispatchEvent.LISTS,
        {
            "action": "set_repository",
            "repository_id": repository_id,
        },
    )

    _send_result(
        connection,
        msg["id"],
        data,
    )
