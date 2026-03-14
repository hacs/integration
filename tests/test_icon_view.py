from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiohttp import web

from custom_components.hacs.icon_view import HacsRepositoryIconView


def test_icon_view_is_public():
    assert HacsRepositoryIconView.requires_auth is False


async def test_repository_icon_view_raises_not_found_when_no_icon(
    repository_integration,
    monkeypatch,
):
    repository_integration.hacs.repositories.register(repository_integration)
    view = HacsRepositoryIconView(repository_integration.hacs.hass)

    resolver = AsyncMock(return_value=None)
    monkeypatch.setattr("custom_components.hacs.icon_view.async_resolve_repository_icon_url", resolver)

    with pytest.raises(web.HTTPNotFound):
        await view.get(
            SimpleNamespace(query={}),
            str(repository_integration.data.id),
        )


async def test_repository_icon_view_redirects_to_uploaded_image_path(
    repository_integration,
    monkeypatch,
):
    repository_integration.hacs.repositories.register(repository_integration)
    view = HacsRepositoryIconView(repository_integration.hacs.hass)

    resolver = AsyncMock(return_value="/api/image/serve/image_1/original")
    monkeypatch.setattr("custom_components.hacs.icon_view.async_resolve_repository_icon_url", resolver)

    with pytest.raises(web.HTTPFound) as err:
        await view.get(
            SimpleNamespace(query={"dark": "1"}),
            str(repository_integration.data.id),
        )

    assert err.value.location == "/api/image/serve/image_1/original"
