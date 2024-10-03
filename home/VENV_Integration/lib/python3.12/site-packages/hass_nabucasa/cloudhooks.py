"""Manage cloud cloudhooks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import async_timeout

from . import cloud_api

if TYPE_CHECKING:
    from . import Cloud, _ClientT


class Cloudhooks:
    """Class to help manage cloudhooks."""

    def __init__(self, cloud: Cloud[_ClientT]) -> None:
        """Initialize cloudhooks."""
        self.cloud = cloud

        cloud.iot.register_on_connect(self.async_publish_cloudhooks)

    async def async_publish_cloudhooks(self) -> None:
        """Inform the Relayer of the cloudhooks that we support."""
        if not self.cloud.is_connected:
            return

        cloudhooks = self.cloud.client.cloudhooks
        await self.cloud.iot.async_send_message(
            "webhook-register",
            {"cloudhook_ids": [info["cloudhook_id"] for info in cloudhooks.values()]},
            expect_answer=False,
        )

    async def async_create(self, webhook_id: str, managed: bool) -> dict[str, Any]:
        """Create a cloud webhook."""
        cloudhooks = self.cloud.client.cloudhooks

        if webhook_id in cloudhooks:
            raise ValueError("Hook is already enabled for the cloud.")

        if not self.cloud.iot.connected:
            raise ValueError("Cloud is not connected")

        # Create cloud hook
        async with async_timeout.timeout(10):
            resp = await cloud_api.async_create_cloudhook(self.cloud)

        resp.raise_for_status()
        data = await resp.json()
        cloudhook_id = data["cloudhook_id"]
        cloudhook_url = data["url"]

        # Store hook
        cloudhooks = dict(cloudhooks)
        hook = cloudhooks[webhook_id] = {
            "webhook_id": webhook_id,
            "cloudhook_id": cloudhook_id,
            "cloudhook_url": cloudhook_url,
            "managed": managed,
        }
        await self.cloud.client.async_cloudhooks_update(cloudhooks)

        await self.async_publish_cloudhooks()
        return hook

    async def async_delete(self, webhook_id: str) -> None:
        """Delete a cloud webhook."""
        cloudhooks = self.cloud.client.cloudhooks

        if webhook_id not in cloudhooks:
            raise ValueError("Hook is not enabled for the cloud.")

        # Remove hook
        cloudhooks = dict(cloudhooks)
        cloudhooks.pop(webhook_id)
        await self.cloud.client.async_cloudhooks_update(cloudhooks)

        await self.async_publish_cloudhooks()
