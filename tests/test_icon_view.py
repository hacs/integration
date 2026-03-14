from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiohttp import web

from custom_components.hacs.icon_view import (
    HacsRepositoryIconByDomainView,
    HacsRepositoryIconView,
)


def test_icon_views_are_public():
    assert HacsRepositoryIconView.requires_auth is False
    assert HacsRepositoryIconByDomainView.requires_auth is False


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


async def test_domain_icon_view_redirects_unknown_domains_to_brands(hacs):
    view = HacsRepositoryIconByDomainView(hacs.hass)

    with pytest.raises(web.HTTPFound) as err:
        await view.get(SimpleNamespace(query={"dark": "1"}), "unknown_domain")

    assert err.value.location == (
        "https://brands.home-assistant.io/_/unknown_domain/dark_icon.png"
    )
