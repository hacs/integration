from typing import Generator
from unittest.mock import patch

from aiogithubapi import GitHubException
from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, UnknownFlow
import pytest

from custom_components.hacs.const import DOMAIN

from tests.common import (
    TOKEN,
    MockedResponse,
    ResponseMocker,
    recursive_remove_key,
    safe_json_dumps,
)
from tests.conftest import SnapshotFixture


@pytest.fixture
def _mock_setup_entry(hass: HomeAssistant) -> Generator[None, None, None]:
    """Mock setting up a config entry."""
    hass.data.pop("custom_components", None)
    with patch("custom_components.hacs.async_setup_entry", return_value=True):
        yield


async def test_full_user_flow_implementation(
    hass: HomeAssistant,
    _mock_setup_entry: None,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
) -> None:
    """Test the full manual user flow from start to finish."""
    response_mocker.add(
        url="https://github.com/login/device/code",
        response=MockedResponse(
            content={
                "device_code": "3584d83530557fdd1f46af8289938c8ef79f9dc5",
                "user_code": "WDJB-MJHT",
                "verification_uri": "https://github.com/login/device",
                "expires_in": 900,
                "interval": 5,
            },
            headers={"Content-Type": "application/json"},
        ),
    )
    response_mocker.add(
        url="https://github.com/login/oauth/access_token",
        response=MockedResponse(
            content={
                CONF_ACCESS_TOKEN: TOKEN,
                "token_type": "bearer",
                "scope": "",
            },
            headers={"Content-Type": "application/json"},
        ),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["step_id"] == "user"
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "acc_logs": True,
            "acc_addons": True,
            "acc_untested": True,
            "acc_disable": False,
            "experimental": True,
        },
    )

    assert result["errors"] == {"base": "acc"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "acc_logs": True,
            "acc_addons": True,
            "acc_untested": True,
            "acc_disable": True,
            "experimental": True,
        },
    )

    assert result["step_id"] == "device"
    assert result["type"] == FlowResultType.SHOW_PROGRESS

    await hass.config_entries.flow.async_configure(result["flow_id"])
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] == FlowResultType.CREATE_ENTRY

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(result, ("flow_id", "minor_version"))),
        "config_flow/test_full_user_flow_implementation.json",
    )


async def test_flow_with_remove_while_activating(
    hass: HomeAssistant,
    mock_setup_entry: None,
    response_mocker: ResponseMocker,
) -> None:
    """Test flow with user canceling while activating."""
    response_mocker.add(
        url="https://github.com/login/device/code",
        response=MockedResponse(
            content={
                "device_code": "3584d83530557fdd1f46af8289938c8ef79f9dc5",
                "user_code": "WDJB-MJHT",
                "verification_uri": "https://github.com/login/device",
                "expires_in": 900,
                "interval": 5,
            },
            headers={"Content-Type": "application/json"},
        ),
    )
    response_mocker.add(
        url="https://github.com/login/oauth/access_token",
        response=MockedResponse(
            content={"error": "authorization_pending"}, headers={"Content-Type": "application/json"}
        ),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["step_id"] == "user"
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "acc_logs": True,
            "acc_addons": True,
            "acc_untested": True,
            "acc_disable": True,
            "experimental": True,
        },
    )

    assert result["step_id"] == "device"
    assert result["type"] == FlowResultType.SHOW_PROGRESS

    assert hass.config_entries.flow.async_get(result["flow_id"])

    # Simulate user canceling the flow
    hass.config_entries.flow._async_remove_flow_progress(result["flow_id"])
    await hass.async_block_till_done()

    with pytest.raises(UnknownFlow):
        hass.config_entries.flow.async_get(result["flow_id"])


async def test_flow_with_registration_failure(
    hass: HomeAssistant,
    _mock_setup_entry: None,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
) -> None:
    """Test flow with registration failure of the device."""
    response_mocker.add(
        url="https://github.com/login/device/code",
        response=MockedResponse(exception=GitHubException("Registration failed")),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["step_id"] == "user"
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "acc_logs": True,
            "acc_addons": True,
            "acc_untested": True,
            "acc_disable": True,
            "experimental": True,
        },
    )

    assert result["type"] == FlowResultType.ABORT

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(result, ("flow_id", "minor_version"))),
        "config_flow/test_flow_with_registration_failure.json",
    )


async def test_flow_with_activation_failure(
    hass: HomeAssistant,
    _mock_setup_entry: None,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
) -> None:
    """Test flow with activation failure of the device."""
    response_mocker.add(
        url="https://github.com/login/device/code",
        response=MockedResponse(
            content={
                "device_code": "3584d83530557fdd1f46af8289938c8ef79f9dc5",
                "user_code": "WDJB-MJHT",
                "verification_uri": "https://github.com/login/device",
                "expires_in": 900,
                "interval": 5,
            },
            headers={"Content-Type": "application/json"},
        ),
    )
    response_mocker.add(
        url="https://github.com/login/oauth/access_token",
        response=MockedResponse(exception=GitHubException("Activation failed")),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["step_id"] == "user"
    assert result["type"] == FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            "acc_logs": True,
            "acc_addons": True,
            "acc_untested": True,
            "acc_disable": True,
            "experimental": True,
        },
    )

    assert result["step_id"] == "device"
    assert result["type"] == FlowResultType.SHOW_PROGRESS

    await hass.config_entries.flow.async_configure(result["flow_id"])
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] == FlowResultType.ABORT

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(result, ("flow_id", "minor_version"))),
        "config_flow/test_flow_with_activation_failure.json",
    )


async def test_already_configured(
    hass: HomeAssistant,
    _mock_setup_entry: None,
    snapshots: SnapshotFixture,
) -> None:
    """Test we abort if already configured."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] == FlowResultType.ABORT
    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(result, ("flow_id", "minor_version"))),
        "config_flow/test_already_configured.json",
    )
