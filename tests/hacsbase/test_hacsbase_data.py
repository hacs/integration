"""Data Test Suite."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hacs.base import HacsRepositories
from custom_components.hacs.enums import HacsGitHubRepo
from custom_components.hacs.utils.data import HacsData


async def test_hacs_data_async_write1(hacs, repository):
    data = HacsData(hacs)
    repository.data.installed = True
    repository.data.installed_version = "1"
    hacs.repositories.register(repository)
    await data.async_write()


async def test_hacs_data_async_write2(hacs):
    data = HacsData(hacs)
    hacs.system.disabled_reason = None
    hacs.repositories = HacsRepositories()
    await data.async_write()


async def test_hacs_data_restore_write_not_new(hacs, caplog):
    data = HacsData(hacs)

    async def _mocked_loads(hass, key):
        if key == "repositories":
            return {
                "123": {"category": "integration"},
                "1727333146": {
                    "category": "integration",
                    "full_name": "hacs/integration2",
                    "installed": True,
                    "show_beta": True,
                },
                "202226247": {
                    "category": "integration",
                    "full_name": "shbatm/hacs-isy994",
                    "installed": False,
                },
            }
        elif key == "hacs":
            return {}
        elif key == "data":
            return {}
        elif key == "renamed_repositories":
            return {}
        else:
            raise ValueError(f"No mock for {key}")

    with (
        patch("os.path.exists", return_value=True),
        patch(
            "custom_components.hacs.utils.data.async_load_from_store",
            side_effect=_mocked_loads,
        ),
    ):
        assert await data.restore() is True

    assert "Skipping registration of repository ID 123: missing full_name" in caplog.text

    assert hacs.repositories.get_by_id("202226247")
    assert hacs.repositories.get_by_full_name("shbatm/hacs-isy994")

    assert hacs.repositories.get_by_id("1727333146")
    assert hacs.repositories.get_by_full_name(HacsGitHubRepo.INTEGRATION)

    assert hacs.repositories.get_by_id("1727333146").data.show_beta is True
    assert hacs.repositories.get_by_id("1727333146").data.installed is True

    with patch("custom_components.hacs.utils.data.async_save_to_store") as mock_async_save_to_store:
        await data.async_write()
    assert mock_async_save_to_store.called
    assert "Loading base repository information" not in caplog.text


@pytest.mark.parametrize("full_name", [None, ""])
async def test_register_unknown_repositories_without_name(full_name, caplog):
    """An incomplete unknown entry must not prevent valid registrations."""
    hacs = MagicMock()
    hacs.repositories.is_registered.return_value = False
    hacs.async_register_repository = AsyncMock()
    incomplete = {"category": "integration"}
    if full_name is not None:
        incomplete["full_name"] = full_name
    repositories = {
        "123": incomplete,
        "456": {"category": "integration", "full_name": "test/valid"},
    }

    await HacsData(hacs).register_unknown_repositories(repositories)

    hacs.async_register_repository.assert_awaited_once_with(
        repository_full_name="test/valid",
        category="integration",
        check=False,
        repository_id="456",
    )
    assert "123" in caplog.text
    assert "full_name" in caplog.text
    assert repositories["123"] == incomplete


async def test_restore_known_repository_without_name(hacs, repository):
    """A known ID can restore metadata even when its saved name is absent."""
    hacs.repositories.register(repository)
    repository_id = str(repository.data.id)
    stored = {repository_id: {"category": "integration", "installed": True, "show_beta": True}}

    async def load_store(hass, key):
        return stored if key == "repositories" else {}

    with patch("custom_components.hacs.utils.data.async_load_from_store", side_effect=load_store):
        assert await HacsData(hacs).restore() is True

    restored = hacs.repositories.get_by_id(repository_id)
    assert restored is repository
    assert restored.data.installed is True
    assert restored.data.show_beta is True
