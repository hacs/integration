"""Data Test Suite."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hacs.base import HacsRepositories
from custom_components.hacs.enums import HacsCategory, HacsGitHubRepo
from custom_components.hacs.repositories import HacsIntegrationRepository
from custom_components.hacs.utils.data import HacsData

KNOWN_REPOSITORY_COUNT = 1000
REPOSITORY_FULL_NAME_CONFLICT = "other/repository"
REPOSITORY_ID_CURRENT = "10"
REPOSITORY_ID_NEXT = "20"
REPOSITORY_ID_STALE = "9"


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


@pytest.mark.parametrize(
    "stored_ids",
    [
        (REPOSITORY_ID_STALE,),
        (REPOSITORY_ID_CURRENT, REPOSITORY_ID_STALE),
        (REPOSITORY_ID_STALE, REPOSITORY_ID_CURRENT),
    ],
    ids=["stale-only", "current-then-stale", "stale-then-current"],
)
async def test_reconcile_recreated_repository_id(
    hacs, repository_integration, caplog, stored_ids
):
    data = HacsData(hacs)
    hacs.repositories = HacsRepositories()
    repository_full_name = repository_integration.data.full_name

    async def _mocked_loads(hass, key):
        if key == "repositories":
            repositories = {}
            for repository_id in stored_ids:
                repositories[repository_id] = {
                    "category": "integration",
                    "full_name": repository_full_name,
                }
                if repository_id == REPOSITORY_ID_STALE:
                    repositories[repository_id]["installed"] = True
            return repositories
        return {}

    with patch(
        "custom_components.hacs.utils.data.async_load_from_store",
        side_effect=_mocked_loads,
    ):
        assert await data.restore()

    stored_repository = hacs.repositories.get_by_id(REPOSITORY_ID_STALE)
    assert stored_repository is not None
    hacs.repositories.mark_default(stored_repository)
    assert "duplicate IDs" not in caplog.text

    category_data = {
        REPOSITORY_ID_CURRENT: {
            "full_name": repository_full_name,
            "last_fetched": 0.0,
        }
    }
    with patch.object(hacs.data_client, "get_data", return_value=category_data):
        await hacs.async_get_category_repositories_experimental(HacsCategory.INTEGRATION)
        repository = hacs.repositories.get_by_id(REPOSITORY_ID_CURRENT)
        await hacs.async_get_category_repositories_experimental(HacsCategory.INTEGRATION)

    assert hacs.repositories.get_by_id(REPOSITORY_ID_STALE) is None
    assert hacs.repositories.get_by_id(REPOSITORY_ID_CURRENT) is stored_repository
    assert hacs.repositories.get_by_id(REPOSITORY_ID_CURRENT) is repository
    assert hacs.repositories.get_by_full_name(repository_full_name) is repository
    assert hacs.repositories.list_all == [stored_repository]
    assert hacs.repositories.is_default(REPOSITORY_ID_CURRENT)
    assert stored_repository.data.installed is True


async def test_reconcile_repository_id_rejects_different_slug(
    hacs, repository_integration
):
    hacs.repositories = HacsRepositories()
    repository_integration.data.id = REPOSITORY_ID_STALE
    repository_integration.data.installed = True
    hacs.repositories.register(repository_integration)
    hacs.repositories.mark_default(repository_integration)
    await hacs.async_register_repository(
        repository_full_name=REPOSITORY_FULL_NAME_CONFLICT,
        category=HacsCategory.INTEGRATION,
        check=False,
        repository_id=REPOSITORY_ID_CURRENT,
    )
    conflicting_repository = hacs.repositories.get_by_id(REPOSITORY_ID_CURRENT)
    assert conflicting_repository is not None

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

    assert hacs.repositories.get_by_id(REPOSITORY_ID_STALE) is repository_integration
    assert hacs.repositories.get_by_id(REPOSITORY_ID_CURRENT) is conflicting_repository
    assert (
        hacs.repositories.get_by_full_name(repository_integration.data.full_name)
        is repository_integration
    )
    assert (
        hacs.repositories.get_by_full_name(REPOSITORY_FULL_NAME_CONFLICT)
        is conflicting_repository
    )
    assert repository_integration.data.installed is True
    assert hacs.repositories.is_default(REPOSITORY_ID_STALE)


@pytest.mark.parametrize("excluded", ["removed", "archived"])
async def test_excluded_repository_is_not_reconciled(
    hacs, repository_integration, excluded
):
    hacs.repositories = HacsRepositories()
    repository_integration.data.id = REPOSITORY_ID_STALE
    repository_integration.data.installed = True
    hacs.repositories.register(repository_integration)
    hacs.repositories.mark_default(repository_integration)
    if excluded == "removed":
        hacs.repositories.removed_repository(repository_integration.data.full_name)
    else:
        hacs.common.archived_repositories.add(repository_integration.data.full_name)

    category_data = {
        REPOSITORY_ID_CURRENT: {
            "full_name": repository_integration.data.full_name,
        }
    }
    with patch.object(hacs.data_client, "get_data", return_value=category_data):
        await hacs.async_get_category_repositories_experimental(HacsCategory.INTEGRATION)

    assert hacs.repositories.get_by_id(REPOSITORY_ID_STALE) is repository_integration
    assert hacs.repositories.get_by_id(REPOSITORY_ID_CURRENT) is None
    assert hacs.repositories.is_default(REPOSITORY_ID_STALE)


async def test_known_catalog_merge_does_not_reconcile(hacs):
    hacs.repositories = HacsRepositories()
    category_data = {}
    last_fetched = datetime.now(UTC)
    for index in range(KNOWN_REPOSITORY_COUNT):
        repository_id = str(index + KNOWN_REPOSITORY_COUNT)
        repository = HacsIntegrationRepository(hacs, f"test/repository-{index}")
        repository.data.id = repository_id
        repository.data.last_fetched = last_fetched
        hacs.repositories.register(repository)
        category_data[repository_id] = {
            "full_name": repository.data.full_name,
            "last_fetched": 0.0,
        }

    with (
        patch.object(hacs.data_client, "get_data", return_value=category_data),
        patch.object(
            hacs.repositories,
            "reconcile_repository_id",
            wraps=hacs.repositories.reconcile_repository_id,
        ) as reconcile_repository_id,
        patch(
            "custom_components.hacs.utils.data.asyncio.sleep",
            new_callable=AsyncMock,
        ) as sleep,
    ):
        await hacs.async_get_category_repositories_experimental(HacsCategory.INTEGRATION)

    assert reconcile_repository_id.call_count == 0
    assert sleep.await_count == KNOWN_REPOSITORY_COUNT // 100
    assert len(hacs.repositories.list_all) == KNOWN_REPOSITORY_COUNT


async def test_known_stored_repository_without_full_name(hacs, repository_integration):
    data = HacsData(hacs)
    hacs.repositories = HacsRepositories()
    repository_integration.data.id = REPOSITORY_ID_CURRENT
    hacs.repositories.register(repository_integration)

    await data.register_unknown_repositories(
        {
            REPOSITORY_ID_CURRENT: {
                "category": HacsCategory.INTEGRATION,
            }
        }
    )


@pytest.mark.parametrize("current_registered_last", [False, True])
async def test_multiple_installed_repositories_prefer_current_id(
    hacs, repository_integration, current_registered_last
):
    hacs.repositories = HacsRepositories()
    repository_integration.data.id = REPOSITORY_ID_CURRENT
    repository_integration.data.installed = True
    stale_repository = HacsIntegrationRepository(
        hacs, repository_integration.data.full_name
    )
    stale_repository.data.id = REPOSITORY_ID_STALE
    stale_repository.data.installed = True
    repositories = (
        (stale_repository, repository_integration)
        if current_registered_last
        else (repository_integration, stale_repository)
    )
    for repository in repositories:
        hacs.repositories.register(repository)
        hacs.repositories.mark_default(repository)

    category_data = {
        REPOSITORY_ID_CURRENT: {
            "full_name": repository_integration.data.full_name,
            "last_fetched": 0.0,
        }
    }
    with patch.object(hacs.data_client, "get_data", return_value=category_data):
        await hacs.async_get_category_repositories_experimental(HacsCategory.INTEGRATION)

    assert hacs.repositories.get_by_id(REPOSITORY_ID_CURRENT) is repository_integration
    assert hacs.repositories.get_by_id(REPOSITORY_ID_STALE) is None
    assert hacs.repositories.list_all == [repository_integration]
    assert hacs.repositories.is_default(REPOSITORY_ID_CURRENT)


@pytest.mark.parametrize("stale_registered_last", [False, True])
async def test_multiple_installed_repositories_use_numeric_id_order(
    hacs, repository_integration, stale_registered_last
):
    hacs.repositories = HacsRepositories()
    repository_integration.data.id = REPOSITORY_ID_CURRENT
    repository_integration.data.installed = True
    stale_repository = HacsIntegrationRepository(
        hacs, repository_integration.data.full_name
    )
    stale_repository.data.id = REPOSITORY_ID_STALE
    stale_repository.data.installed = True
    repositories = (
        (repository_integration, stale_repository)
        if stale_registered_last
        else (stale_repository, repository_integration)
    )
    for repository in repositories:
        hacs.repositories.register(repository)
        hacs.repositories.mark_default(repository)

    category_data = {
        REPOSITORY_ID_NEXT: {
            "full_name": repository_integration.data.full_name,
            "last_fetched": 0.0,
        }
    }
    with patch.object(hacs.data_client, "get_data", return_value=category_data):
        await hacs.async_get_category_repositories_experimental(HacsCategory.INTEGRATION)

    assert hacs.repositories.get_by_id(REPOSITORY_ID_NEXT) is stale_repository
    assert hacs.repositories.get_by_id(REPOSITORY_ID_STALE) is None
    assert hacs.repositories.get_by_id(REPOSITORY_ID_CURRENT) is None
    assert hacs.repositories.list_all == [stale_repository]
    assert hacs.repositories.is_default(REPOSITORY_ID_NEXT)
