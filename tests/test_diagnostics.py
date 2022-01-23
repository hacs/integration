"""Test the diagnostics module."""
from unittest.mock import MagicMock, patch

from aiogithubapi import GitHubException, GitHubRateLimitModel, GitHubResponseModel
from homeassistant.components.diagnostics import REDACTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.diagnostics import async_get_config_entry_diagnostics

from tests.common import TOKEN


@pytest.mark.asyncio
async def test_diagnostics(hacs: HacsBase, hass: HomeAssistant, config_entry: ConfigEntry):
    """Test the base result."""
    response = GitHubResponseModel(MagicMock(headers={}))
    response.data = GitHubRateLimitModel({"resources": {"core": {"remaining": 0}}})
    with patch("aiogithubapi.github.GitHub.rate_limit", return_value=response):
        diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["hacs"]["version"] == "0.0.0"
    assert diagnostics["rate_limit"]["resources"]["core"]["remaining"] == 0
    assert TOKEN not in str(diagnostics)
    assert diagnostics["entry"]["data"]["token"] == REDACTED


@pytest.mark.asyncio
async def test_diagnostics_with_exception(
    hacs: HacsBase, hass: HomeAssistant, config_entry: ConfigEntry
):
    """test the result with issues getting the ratelimit."""
    with patch(
        "aiogithubapi.github.GitHub.rate_limit", side_effect=GitHubException("Something went wrong")
    ):
        diagnostics = await async_get_config_entry_diagnostics(hass, config_entry)

    assert diagnostics["hacs"]["version"] == "0.0.0"
    assert diagnostics["rate_limit"] == "Something went wrong"
