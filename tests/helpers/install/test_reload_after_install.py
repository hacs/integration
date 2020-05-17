"""Helpers: Install: reload_after_install."""
# pylint: disable=missing-docstring
import pytest

from custom_components.hacs.helpers.install import reload_after_install
from tests.dummy_repository import dummy_repository_integration, dummy_repository_theme


@pytest.mark.asyncio
async def test_reload_after_install():
    repository = dummy_repository_integration()

    await reload_after_install(repository)
    assert repository.pending_restart

    repository.data.config_flow = True
    await reload_after_install(repository)

    repository = dummy_repository_theme()
    await reload_after_install(repository)
