"""Test my hello Home Assistant integration."""
import sys
from unittest.mock import MagicMock, patch

from homeassistant.components.websocket_api import DOMAIN as WEBSOCKET_DOMAIN

import pytest
from custom_components.hacs.base import HacsBase

from tests.common import create_config_entry, get_hacs
from tests.conftest import SnapshotFixture
from custom_components.hello_home_assistant.config_flow import (
    HelloHomeAssistantConfigFlow,
)
from homeassistant.core import HomeAssistant


@pytest.fixture
def config_flow():
    """Fixture to provide the config flow."""
    return HelloHomeAssistantConfigFlow()


@pytest.mark.asyncio
async def test_show_form(hass: HomeAssistant, config_flow) -> None:
    """Test that the form is shown."""
    result = await config_flow.async_step_user(None)
    assert result["type"] == "form"
    assert result["step_id"] == "user"


@pytest.mark.asyncio
async def test_create_entry(hass: HomeAssistant, config_flow) -> None:
    """Test that the entry is created."""
    user_input = {
        "name": "Hello 1",
        "string": "Hello Home Assistant",
        "integer": 123,
    }
    result = await config_flow.async_step_user(user_input)
    assert result["type"] == "create_entry"
    assert result["title"] == "Hello Home Assistant"
    assert result["data"] == user_input
