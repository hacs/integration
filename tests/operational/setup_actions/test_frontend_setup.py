import json
import os

import pytest

from custom_components.hacs.operational.setup_actions.frontend import (
    async_setup_frontend,
)


@pytest.mark.asyncio
async def test_frontend_setup(hacs, tmpdir):
    hacs.system.config_path = tmpdir

    content = {}

    os.makedirs(f"{hacs.system.config_path}/custom_components/hacs", exist_ok=True)

    with open(
        f"{hacs.system.config_path}/custom_components/hacs/manifest.json", "w"
    ) as manifest:
        manifest.write(json.dumps(content))
    await async_setup_frontend()
