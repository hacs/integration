import pytest
from custom_components.hacs.operational.setup_actions.websocket_api import (
    async_setup_hacs_websockt_api,
)


@pytest.mark.asyncio
async def test_async_setup_hacs_websockt_api():
    await async_setup_hacs_websockt_api()
