"""Repairs platform for HACS."""

from __future__ import annotations

from typing import Any

from homeassistant import data_entry_flow
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers.issue_registry import async_delete_issue
import voluptuous as vol

from custom_components.hacs.base import HacsBase

from .const import DOMAIN


class RestartRequiredFixFlow(RepairsFlow):
    """Handler for an issue fixing flow."""

    def __init__(self, issue_id: str) -> None:
        self.issue_id = issue_id

    async def async_step_init(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle the first step of a fix flow."""
        return self.async_show_menu(
            step_id="init",
            menu_options=["restart", "ignore"],
            description_placeholders={"name": self._get_name()},
        )

    async def async_step_restart(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle restart"""
        await self.hass.services.async_call("homeassistant", "restart")
        return self.async_create_entry(title="", data={})

    async def async_step_ignore(
        self, user_input: dict[str, str] | None = None
    ) -> data_entry_flow.FlowResult:
        """Handle ignore"""
        async_delete_issue(self.hass, DOMAIN, self.issue_id)
        return self.async_abort(
            reason="issue_ignored",
            description_placeholders={"name": self._get_name()},
        )

    def _get_name(self) -> str:
        """Get integration display name."""
        hacs: HacsBase = self.hass.data[DOMAIN]
        integration = hacs.repositories.get_by_id(self.issue_id.split("_")[2])

        return integration.display_name


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, str | int | float | None] | None = None,
    *args: Any,
    **kwargs: Any,
) -> RepairsFlow | None:
    """Create flow."""
    if issue_id.startswith("restart_required"):
        return RestartRequiredFixFlow(issue_id)
    return None
