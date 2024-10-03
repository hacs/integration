"""ThingTalk helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from . import Cloud, _ClientT


class ThingTalkConversionError(Exception):
    """Conversion error occurred."""


async def async_convert(cloud: Cloud[_ClientT], query: str) -> dict[str, Any]:
    """Convert sentence."""
    resp = await cloud.client.websession.post(
        f"https://{cloud.thingtalk_server}/convert",
        json={"query": query},
    )
    if resp.status in (200, 201):
        content: dict[str, Any] = await resp.json()
        return content

    try:
        body = await resp.json()
    except ValueError:
        # Invalid JSON in body
        resp.raise_for_status()

    if not isinstance(body, dict) or "error" not in body:
        resp.raise_for_status()

    raise ThingTalkConversionError(body["error"])
