"""Data Test Suite."""
from unittest.mock import patch

import pytest

from custom_components.hacs.base import HacsRepositories
from custom_components.hacs.enums import HacsCategory, HacsGitHubRepo
from custom_components.hacs.utils.data import HacsData

REPOSITORY_FULL_NAME_CONFLICT = "other/repository"
REPOSITORY_ID_CURRENT = "200"
REPOSITORY_ID_STALE = "100"


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

    with patch("os.path.exists", return_value=True), patch(
        "custom_components.hacs.utils.data.async_load_from_store",
        side_effect=_mocked_loads,
    ):
        await data.restore()

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


async def test_reconcile_recreated_repository_id(hacs, repository_integration, caplog):
    data = HacsData(hacs)
    hacs.repositories = HacsRepositories()
    repository_full_name = repository_integration.data.full_name

    async def _mocked_loads(hass, key):
        if key == "repositories":
            return {
                REPOSITORY_ID_CURRENT: {
                    "category": "integration",
                    "full_name": repository_full_name,
                },
                REPOSITORY_ID_STALE: {
                    "category": "integration",
                    "full_name": repository_full_name,
                    "installed": True,
                }
            }
        return {}

    with patch(
        "custom_components.hacs.utils.data.async_load_from_store",
        side_effect=_mocked_loads,
    ):
        assert await data.restore()

    stored_repository = hacs.repositories.get_by_id(REPOSITORY_ID_STALE)
    assert stored_repository is not None
    assert hacs.repositories.get_by_id(REPOSITORY_ID_CURRENT) is not None
    assert "duplicate IDs" not in caplog.text

    category_data = {
        REPOSITORY_ID_CURRENT: {
            "full_name": repository_full_name,
            "last_fetched": 0,
        }
    }
    with patch.object(hacs.data_client, "get_data", return_value=category_data):
        await hacs.async_get_category_repositories_experimental(HacsCategory.INTEGRATION)

    assert hacs.repositories.get_by_id(REPOSITORY_ID_STALE) is None
    assert hacs.repositories.get_by_id(REPOSITORY_ID_CURRENT) is stored_repository
    assert hacs.repositories.list_all == [stored_repository]
    assert hacs.repositories.is_default(REPOSITORY_ID_CURRENT)
    assert stored_repository.data.installed is True


async def test_reconcile_repository_id_rejects_different_slug(
    hacs, repository_integration
):
    hacs.repositories = HacsRepositories()
    repository_integration.data.id = REPOSITORY_ID_STALE
    hacs.repositories.register(repository_integration)
    await hacs.async_register_repository(
        repository_full_name=REPOSITORY_FULL_NAME_CONFLICT,
        category=HacsCategory.INTEGRATION,
        check=False,
        repository_id=REPOSITORY_ID_CURRENT,
    )

    category_data = {
        REPOSITORY_ID_CURRENT: {
            "full_name": repository_integration.data.full_name,
        }
    }
    with (
        patch.object(hacs.data_client, "get_data", return_value=category_data),
        pytest.raises(ValueError, match=f"already set to {REPOSITORY_FULL_NAME_CONFLICT}"),
    ):
        await hacs.async_get_category_repositories_experimental(HacsCategory.INTEGRATION)
