# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import AsyncMock, patch

from aiogithubapi import GitHubNotModifiedException
import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import VERSION_STORAGE
from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.repositories.base import HacsRepository


@pytest.mark.asyncio
async def test_update_critical_repositories_no_critical(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_critical_repositories")

    assert task

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        return_value=[],
    ), patch("custom_components.hacs.utils.store.json_util.load_json") as load_json_mock:
        await task.execute_task()
        assert "No critical repositories" in caplog.text
        load_json_mock.assert_not_called()


@pytest.mark.asyncio
async def test_update_critical_repositories_exception(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_critical_repositories")

    assert task

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        side_effect=GitHubNotModifiedException("err"),
    ), patch("custom_components.hacs.utils.store.json_util.load_json") as load_json_mock:
        await task.execute_task()
        load_json_mock.assert_not_called()
        assert "No critical repositories" not in caplog.text

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        side_effect=HacsException("err"),
    ), patch("custom_components.hacs.utils.store.json_util.load_json") as load_json_mock:
        await task.execute_task()
        load_json_mock.assert_not_called()
        assert "No critical repositories" in caplog.text


@pytest.mark.asyncio
async def test_update_critical_repositories_update_in_stored(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
):
    hacs.data.async_write = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_critical_repositories")

    assert task

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        return_value=[{"repository": "test/test", "reason": "test", "link": "test"}],
    ), patch(
        "custom_components.hacs.utils.store.json_util.load_json",
        return_value={
            "version": VERSION_STORAGE,
            "data": [{"acknowledged": True, "repository": "test/test"}],
        },
    ):
        await task.execute_task()
        assert "Resarting Home Assistant" not in caplog.text
        assert "The queue is empty" in caplog.text


@pytest.mark.asyncio
async def test_update_critical_repositories_update_not_in_stored_not_installed(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
    repository: HacsRepository,
):
    hacs.data.async_write = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_critical_repositories")

    assert task

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        return_value=[{"repository": "test/test", "reason": "test", "link": "test"}],
    ), patch(
        "custom_components.hacs.utils.store.json_util.load_json",
        return_value={
            "version": VERSION_STORAGE,
            "data": [],
        },
    ), patch(
        "custom_components.hacs.base.HacsRepositories.get_by_full_name",
        return_value=repository,
    ):
        await task.execute_task()
        assert "Resarting Home Assistant" not in caplog.text
        assert "The queue is empty" in caplog.text


@pytest.mark.asyncio
async def test_update_critical_repositories_update_not_in_stored_installed(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
    repository: HacsRepository,
):
    hacs.data.async_write = AsyncMock()
    await hacs.tasks.async_load()
    task = hacs.tasks.get("update_critical_repositories")

    assert task

    repository.data.installed = True

    with patch(
        "custom_components.hacs.base.HacsBase.async_github_get_hacs_default_file",
        return_value=[{"repository": "test/test", "reason": "test", "link": "test"}],
    ), patch(
        "custom_components.hacs.utils.store.json_util.load_json",
        return_value={
            "version": VERSION_STORAGE,
            "data": [],
        },
    ), patch(
        "custom_components.hacs.base.HacsRepositories.get_by_full_name",
        return_value=repository,
    ), patch(
        "custom_components.hacs.repositories.base.HacsRepository.uninstall",
        return_value=AsyncMock(),
    ) as uninstall_mock, patch(
        "homeassistant.core.HomeAssistant.async_stop",
        return_value=AsyncMock(),
    ) as async_stop_mock:
        await task.execute_task()
        uninstall_mock.assert_called()
        async_stop_mock.assert_called()
        assert "Resarting Home Assistant" in caplog.text
        assert "Queue execution finished for 1 tasks finished" in caplog.text
