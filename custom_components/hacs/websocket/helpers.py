"""Helpers for the HACS websocket API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.components import websocket_api

    from ..base import HacsBase
    from ..repositories.base import HacsRepository


def resolve_repository(
    hacs: HacsBase,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    repository_id: str,
) -> HacsRepository | None:
    """Resolve a repository by id, send an error when it is unknown.

    A stale frontend can reference repositories that no longer exist,
    the caller should return early when this returns None.
    """
    if (repository := hacs.repositories.get_by_id(repository_id)) is None:
        connection.send_error(
            msg["id"],
            "repository_not_found",
            f"Repository with ID ({repository_id}) not found",
        )

    return repository
