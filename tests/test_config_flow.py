import asyncio
from collections.abc import Generator
from unittest.mock import patch

from aiogithubapi import GitHubException
from freezegun.api import FrozenDateTimeFactory
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
    create_config_entry,
    get_hacs,
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
    time_freezer: FrozenDateTimeFactory,
    hass: HomeAssistant,
    _mock_setup_entry: None,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    check_report_issue: None,
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

    access_token_responses = [
        # User has not yet entered the code
        {"error": "authorization_pending"},
        # User enters the code
        {CONF_ACCESS_TOKEN: TOKEN, "token_type": "bearer", "scope": ""},
    ]

    async def json(**kwargs):
        return access_token_responses.pop(0)

    response_mocker.add(
        url="https://github.com/login/oauth/access_token",
        response=MockedResponse(
            json=json, headers={"Content-Type": "application/json"}, keep=True),
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
        },
    )

    assert result["step_id"] == "device"
    assert result["type"] == FlowResultType.SHOW_PROGRESS

    time_freezer.tick(10)
    await hass.async_block_till_done()

    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] == FlowResultType.CREATE_ENTRY

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(
            result, ("flow_id", "minor_version"))),
        "config_flow/test_full_user_flow_implementation.json",
    )


async def test_flow_with_remove_while_activating(
    hass: HomeAssistant,
    _mock_setup_entry: None,
    response_mocker: ResponseMocker,
    check_report_issue: None,
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

    access_token_event = asyncio.Event()

    async def json(**kwargs):
        access_token_event.set()
        return {"error": "authorization_pending"}

    response_mocker.add(
        url="https://github.com/login/oauth/access_token",
        response=MockedResponse(
            json=json, headers={"Content-Type": "application/json"}, keep=True),
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
        },
    )

    assert result["step_id"] == "device"
    assert result["type"] == FlowResultType.SHOW_PROGRESS

    # Wait for access token request
    await access_token_event.wait()

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
    check_report_issue: None,
) -> None:
    """Test flow with registration failure of the device."""
    response_mocker.add(
        url="https://github.com/login/device/code",
        response=MockedResponse(
            exception=GitHubException("Registration failed")),
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
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(
            result, ("flow_id", "minor_version"))),
        "config_flow/test_flow_with_registration_failure.json",
    )


async def test_flow_with_activation_failure(
    time_freezer: FrozenDateTimeFactory,
    hass: HomeAssistant,
    _mock_setup_entry: None,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    check_report_issue: None,
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

    def raise_github_exception() -> None:
        raise GitHubException("Activation failed")

    access_token_responses = [
        # User has not yet entered the code
        lambda: {"error": "authorization_pending"},
        # Activation fails
        raise_github_exception,
    ]

    async def json(**kwargs):
        return access_token_responses.pop(0)()

    response_mocker.add(
        url="https://github.com/login/oauth/access_token",
        response=MockedResponse(
            json=json, headers={"Content-Type": "application/json"}, keep=True),
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
        },
    )

    assert result["step_id"] == "device"
    assert result["type"] == FlowResultType.SHOW_PROGRESS

    time_freezer.tick(10)

    await hass.config_entries.flow.async_configure(result["flow_id"])
    await hass.async_block_till_done()
    result = await hass.config_entries.flow.async_configure(result["flow_id"])
    assert result["type"] == FlowResultType.ABORT

    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(
            result, ("flow_id", "minor_version"))),
        "config_flow/test_flow_with_activation_failure.json",
    )


async def test_already_configured(
    hass: HomeAssistant,
    _mock_setup_entry: None,
    snapshots: SnapshotFixture,
    check_report_issue: None,
) -> None:
    """Test we abort if already configured."""
    config_entry = create_config_entry()
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )
    await hass.async_block_till_done()

    assert result["type"] == FlowResultType.ABORT
    snapshots.assert_match(
        safe_json_dumps(recursive_remove_key(
            result, ("flow_id", "minor_version"))),
        "config_flow/test_already_configured.json",
    )


async def test_options_flow(hass: HomeAssistant, setup_integration: Generator) -> None:
    """Test reconfiguring."""
    config_entry = hass.config_entries.async_entries(DOMAIN)[0]
    result = await hass.config_entries.options.async_init(config_entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Test defaults
    hacs = get_hacs(hass)
    schema = result["data_schema"].schema
    for key in schema:
        assert key.default() == getattr(hacs.configuration, str(key))

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "sidepanel_title": "new_title",
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        "appdaemon": True,
        "country": "ALL",
        "experimental": True,
        "sidepanel_icon": "hacs:hacs",
        "sidepanel_title": "new_title",
    }
    assert config_entry.data == {"token": TOKEN}
    assert config_entry.options == {
        "appdaemon": True,
        "country": "ALL",
        "experimental": True,
        "sidepanel_icon": "hacs:hacs",
        "sidepanel_title": "new_title",
    }

    # Check config entry is reloaded with new options
    await hass.async_block_till_done()

    # Get a new HACS instance after reload
    hacs = get_hacs(hass)
    for key, val in config_entry.options.items():
        if key == "experimental":
            assert hasattr(hacs.configuration, str(key)) is False
            continue
        assert getattr(hacs.configuration, str(key)) == val
