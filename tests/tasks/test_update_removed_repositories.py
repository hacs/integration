# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hacs.base import HacsBase, HacsRepositories
from custom_components.hacs.enums import HacsDisabledReason
from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.repositories.base import HacsRepository
from custom_components.hacs.utils.data import HacsData


@pytest.mark.asyncio
async def test_update_removed_repositories_no_removed(hacs: HacsBase):
    hacs.data.async_write = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_removed_repositories")

    assert task

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        return_value=[],
    ), patch(
        "custom_components.hacs.repositories.base.HacsRepository.remove",
        return_value=MagicMock(),
    ) as remove_mock:
        await task.execute_task()
        hacs.data.async_write.assert_not_called()
        remove_mock.assert_not_called()


@pytest.mark.asyncio
async def test_update_removed_repositories_exception(hacs: HacsBase):
    hacs.data.async_write = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_removed_repositories")

    assert task

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        side_effect=HacsException("err"),
    ), patch(
        "custom_components.hacs.repositories.base.HacsRepository.remove",
        return_value=MagicMock(),
    ) as remove_mock:
        await task.execute_task()
        hacs.data.async_write.assert_not_called()
        remove_mock.assert_not_called()


@pytest.mark.asyncio
async def test_update_removed_repositories_not_tracked(hacs: HacsBase):
    hacs.data.async_write = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_removed_repositories")

    assert task

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        return_value=[{"repository": "test/test"}],
    ), patch(
        "custom_components.hacs.repositories.base.HacsRepository.remove",
        return_value=MagicMock(),
    ) as remove_mock:
        await task.execute_task()
        hacs.data.async_write.assert_not_called()
        remove_mock.assert_not_called()


@pytest.mark.asyncio
async def test_update_removed_repositories_installed_not_critical(
    hacs: HacsBase,
    repository: HacsRepository,
    caplog: pytest.LogCaptureFixture,
):
    hacs.data.async_write = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_removed_repositories")

    assert task

    repository.data.installed = True

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        return_value=[{"repository": "test/test", "removal_type": "generic"}],
    ), patch(
        "custom_components.hacs.base.HacsRepositories.get_by_full_name",
        return_value=repository,
    ), patch(
        "custom_components.hacs.repositories.base.HacsRepository.remove",
        return_value=MagicMock(),
    ) as remove_mock:
        await task.execute_task()
        hacs.data.async_write.assert_not_called()
        remove_mock.assert_not_called()
        assert (
            "You have 'test/test' installed with HACS this repository has been removed from HACS"
            in caplog.text
        )


@pytest.mark.asyncio
async def test_update_removed_repositories_installed_critical(
    hacs: HacsBase,
    repository: HacsRepository,
    caplog: pytest.LogCaptureFixture,
):
    hacs.data.async_write = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_removed_repositories")

    assert task

    repository.data.installed = True

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        return_value=[{"repository": "test/test", "removal_type": "critical"}],
    ), patch(
        "custom_components.hacs.base.HacsRepositories.get_by_full_name",
        return_value=repository,
    ), patch(
        "custom_components.hacs.repositories.base.HacsRepository.remove",
        return_value=MagicMock(),
    ) as remove_mock:
        await task.execute_task()
        hacs.data.async_write.assert_called()
        remove_mock.assert_called()
        assert (
            "You have 'test/test' installed with HACS this repository has been removed from HACS"
            not in caplog.text
        )


@pytest.mark.asyncio
async def test_update_removed_repositories_not_installed_critical(
    hacs: HacsBase,
    repository: HacsRepository,
    caplog: pytest.LogCaptureFixture,
):
    hacs.data.async_write = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_removed_repositories")

    assert task

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        return_value=[{"repository": "test/test", "removal_type": "critical"}],
    ), patch(
        "custom_components.hacs.base.HacsRepositories.get_by_full_name",
        return_value=repository,
    ), patch(
        "custom_components.hacs.repositories.base.HacsRepository.remove",
        return_value=MagicMock(),
    ) as remove_mock:
        await task.execute_task()
        hacs.data.async_write.assert_called()
        remove_mock.assert_called()
        assert (
            "You have 'test/test' installed with HACS this repository has been removed from HACS"
            not in caplog.text
        )
