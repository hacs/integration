import json
import os
import pytest
from custom_components.hacs.operational.setup_actions.frontend import (
    async_setup_frontend,
)


from custom_components.hacs.share import get_hacs
from homeassistant.core import HomeAssistant


class MockHTTP:
    def register_view(self, _):
        pass


class MockFrontend:
    def async_register_built_in_panel(self, **kwargs):
        pass


class MockComponents:
    @property
    def frontend(self):
        return MockFrontend()


@pytest.mark.asyncio
async def test_frontend_setup(tmpdir):
    hacs = get_hacs()
    hacs.system.config_path = tmpdir
    hacs.hass = HomeAssistant()
    hacs.hass.components = MockComponents()
    hacs.hass.http = MockHTTP()

    content = {}

    os.makedirs(f"{hacs.system.config_path}/custom_components/hacs", exist_ok=True)

    with open(
        f"{hacs.system.config_path}/custom_components/hacs/manifest.json", "w"
    ) as manifest:
        manifest.write(json.dumps(content))
    await async_setup_frontend()

    # Reset
    hacs.hass = HomeAssistant()
