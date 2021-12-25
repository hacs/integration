# pylint: disable=missing-function-docstring,missing-module-docstring, protected-access
from unittest.mock import AsyncMock, patch

import pytest

from custom_components.hacs.base import HacsBase, HacsRepositories
from custom_components.hacs.enums import HacsDisabledReason
from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.repositories.base import HacsRepository


@pytest.mark.asyncio
async def test_load_hacs_repository_exist(hacs: HacsBase, repository: HacsRepository):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("load_hacs_repository")

    assert task

    assert not repository.data.installed

    with patch(
        "custom_components.hacs.base.HacsRepositories.get_by_full_name", return_value=repository
    ):
        await task.execute_task()
        assert repository.data.installed


@pytest.mark.asyncio
async def test_load_hacs_repository_register_failed(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("load_hacs_repository")

    assert task

    assert not hacs.system.disabled

    with patch(
        "custom_components.hacs.tasks.load_hacs_repository.register_repository", AsyncMock()
    ):
        await task.execute_task()
        assert hacs.system.disabled
        assert hacs.system.disabled_reason == HacsDisabledReason.LOAD_HACS
        assert "[Unknown error] - Could not load HACS!" in caplog.text


@pytest.mark.asyncio
async def test_load_hacs_repository_register_failed_rate_limit(
    hacs: HacsBase,
    caplog: pytest.LogCaptureFixture,
):
    await hacs.tasks.async_load()
    task = hacs.tasks.get("load_hacs_repository")

    assert task

    assert not hacs.system.disabled

    with patch(
        "custom_components.hacs.tasks.load_hacs_repository.register_repository",
        side_effect=HacsException("ratelimit 403"),
    ):
        await task.execute_task()
        assert hacs.system.disabled
        assert hacs.system.disabled_reason == HacsDisabledReason.LOAD_HACS
        assert "GitHub API is ratelimited, or the token is wrong." in caplog.text
