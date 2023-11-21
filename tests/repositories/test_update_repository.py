from glob import iglob
import os
from typing import Generator
from unittest.mock import ANY

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
import pytest

from custom_components.hacs.const import DOMAIN
from custom_components.hacs.enums import HacsCategory

from tests.common import get_hacs
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "category,from_version,to_version",
    ((HacsCategory.INTEGRATION, "1.0.0", "2.0.0"), (HacsCategory.TEMPLATE, "1.0.0", "2.0.0")),
)
@pytest.mark.asyncio
async def test_update_repository(
    hass: HomeAssistant,
    setup_integration: Generator,
    category: HacsCategory,
    from_version: str,
    to_version: str,
    snapshots: SnapshotFixture,
):
    hacs = get_hacs(hass)
    full_name = f"octocat/{category.value}"
    repo = hacs.repositories.get_by_full_name(full_name)

    assert repo is not None

    await repo.async_install(version=from_version)
    assert repo.data.installed is True
    assert repo.data.installed_version == from_version

    await hass.config_entries.async_reload(hacs.configuration.config_entry.entry_id)

    await hass.async_block_till_done()

    er = async_get_entity_registry(hacs.hass)

    entity_id = er.async_get_entity_id("update", DOMAIN, repo.data.id)

    await hass.services.async_call(
        "update",
        "install",
        service_data={"entity_id": entity_id, "version": to_version, "backup": False},
        blocking=True,
    )

    assert repo.data.installed_version == to_version

    downloaded = [
        f.replace(f"{hacs.core.config_path}", "/config")
        for f in iglob(f"{hacs.core.config_path}/**", recursive=True)
        if os.path.isfile(f)
    ]
    assert len(downloaded) != 0

    await snapshots.assert_hacs_data(hacs, f"{category.value}_test_update_repository.json")
