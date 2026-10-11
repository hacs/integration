"""Uninstall integrations that share a local directory."""

from pathlib import Path
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, issue_registry as ir
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import DOMAIN
from custom_components.hacs.enums import HacsDispatchEvent
from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.repositories.integration import HacsIntegrationRepository
from custom_components.hacs.utils.store import (
    async_load_from_store,
    async_save_to_store,
)

from tests.common import create_config_entry


@pytest.fixture
def local_hacs(hass: HomeAssistant) -> HacsBase:
    """Use the actual repository registry without fetching a catalog."""
    hacs = HacsBase()
    hacs.hass = hass
    hacs.core.config_path = hass.config.path()
    return hacs


def integration(
    hacs: HacsBase, repository_id: str, domain: str = "shared_component", *, installed: bool = True
) -> HacsIntegrationRepository:
    repository = HacsIntegrationRepository(hacs, f"example/integration-{repository_id}")
    repository.data.id = repository_id
    repository.data.domain = domain
    repository.data.installed = installed
    repository.data.installed_version = "1.0.0" if installed else None
    repository.data.installed_commit = "1234567" if installed else None
    repository.content.path.local = repository.localpath
    hacs.repositories.register(repository)
    return repository


def component_file(repository: HacsIntegrationRepository) -> Path:
    path = Path(repository.localpath, "__init__.py")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# installed integration\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("suffix", ["", "/", "/.", "/../shared_component"])
async def test_keep_directory_of_another_installed_repository(local_hacs: HacsBase, suffix: str):
    repository = integration(local_hacs, "1")
    other = integration(local_hacs, "2")
    path = component_file(repository)
    repository.content.path.local += suffix

    assert await repository.remove_local_directory() is True

    assert path.read_text(encoding="utf-8") == "# installed integration\n"
    assert other.data.installed is True


@pytest.mark.parametrize("other_state", ["absent", "not_installed", "different_path", "same_id"])
async def test_remove_exclusively_installed_directory(local_hacs: HacsBase, other_state: str):
    repository = integration(local_hacs, "1")
    path = component_file(repository)
    if other_state == "not_installed":
        integration(local_hacs, "2", installed=False)
    elif other_state == "different_path":
        other = integration(local_hacs, "2", domain="another_component")
        other_path = component_file(other)
    elif other_state == "same_id":
        # A second object with the same logical ID must not count as another owner.
        other = HacsIntegrationRepository(local_hacs, "example/renamed-integration")
        other.data.id = 1
        other.data.domain = repository.data.domain
        other.data.installed = True
        local_hacs.repositories._repositories.add(other)

    assert await repository.remove_local_directory() is True

    assert not path.parent.exists()
    if other_state == "different_path":
        assert other_path.exists()


async def test_shared_legacy_domain_override(local_hacs: HacsBase):
    repository = integration(local_hacs, "1")
    repository.data.full_name = "custom-components/sensor.custom_aftership"
    repository.data.domain = None
    repository.content.path.local = repository.localpath
    other = integration(local_hacs, "2", domain="custom_aftership")
    path = component_file(other)

    assert await repository.remove_local_directory() is True

    assert repository.data.domain == "custom_aftership"
    assert repository.content.path.local == other.localpath
    assert path.exists()


async def test_compare_actual_removal_path_instead_of_domain(local_hacs: HacsBase):
    repository = integration(local_hacs, "1")
    other = integration(local_hacs, "2")
    current_file = component_file(other)
    obsolete_directory = current_file.parent.with_name("obsolete_component")
    obsolete_directory.mkdir()
    repository.content.path.local = str(obsolete_directory)

    assert await repository.remove_local_directory() is True

    assert not obsolete_directory.exists()
    assert current_file.exists()
    assert other.data.installed is True


@pytest.mark.parametrize("failure", ["missing_domain", "unsafe_path", "filesystem"])
async def test_failed_removal_preserves_installation_metadata(local_hacs: HacsBase, failure: str):
    repository = integration(local_hacs, "1")
    path = component_file(repository)
    if failure == "missing_domain":
        repository.data.domain = None
    elif failure == "unsafe_path":
        repository.content.path.local = str(path.parent.parent)

    with (
        patch(
            "custom_components.hacs.repositories.base.async_remove_directory",
            side_effect=OSError("Cannot remove the directory"),
        ) as remove_directory,
        patch("custom_components.hacs.repositories.base.async_remove_store") as remove_store,
        patch.object(repository, "async_remove_entity_device") as remove_device,
    ):
        with pytest.raises(HacsException, match="Could not uninstall"):
            await repository.uninstall()

        remove_store.assert_not_awaited()
        remove_device.assert_not_awaited()
        assert remove_directory.await_count == (failure == "filesystem")

    assert path.exists()
    assert repository.data.installed is True
    assert repository.data.installed_version == "1.0.0"
    assert repository.data.installed_commit == "1234567"
    assert repository.pending_restart is False


async def test_uninstall_missing_directory(local_hacs: HacsBase):
    repository = integration(local_hacs, "1")
    assert not Path(repository.localpath).exists()

    await repository.uninstall()

    assert repository.data.installed is False
    assert repository.data.installed_version is None
    assert repository.data.installed_commit is None


async def test_uninstall_shared_directory_cleans_only_own_metadata(
    local_hacs: HacsBase, hass: HomeAssistant
):
    repository = integration(local_hacs, "1")
    other = integration(local_hacs, "2")
    path = component_file(other)
    config_entry = create_config_entry()
    config_entry.add_to_hass(hass)
    local_hacs.configuration.config_entry = config_entry
    devices = dr.async_get(hass)
    issues = ir.async_get(hass)
    repository_devices = {}
    for entry in (repository, other):
        repository_devices[entry.data.id] = devices.async_get_or_create(
            config_entry_id=config_entry.entry_id, identifiers={(DOMAIN, entry.data.id)}
        )
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"removed_{entry.data.id}",
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key="removed",
        )
        await async_save_to_store(hass, f"hacs/{entry.data.id}.hacs", {"id": entry.data.id})

    with patch.object(local_hacs, "async_dispatch") as dispatch:
        await repository.uninstall()

    assert path.exists()
    assert repository.data.installed is False
    assert repository.data.installed_version is None
    assert repository.data.installed_commit is None
    assert repository.pending_restart is True
    assert other.data.installed is True
    assert other.data.installed_version == "1.0.0"
    assert other.data.installed_commit == "1234567"
    assert other.pending_restart is False
    assert await async_load_from_store(hass, "hacs/1.hacs") == {}
    assert await async_load_from_store(hass, "hacs/2.hacs") == {"id": "2"}
    assert devices.async_get(repository_devices["1"].id) is None
    assert devices.async_get(repository_devices["2"].id) is not None
    assert issues.async_get_issue(DOMAIN, "removed_1") is None
    assert issues.async_get_issue(DOMAIN, "removed_2") is not None
    dispatch.assert_called_once_with(
        HacsDispatchEvent.REPOSITORY,
        {
            "id": 1337,
            "action": "uninstall",
            "repository": repository.data.full_name,
            "repository_id": "1",
        },
    )

    # Once the remaining repository is removed, the directory is exclusive again.
    await other.uninstall()
    assert not path.parent.exists()
    assert other.data.installed is False
