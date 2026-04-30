"""Test HACS brand icon view."""

from types import SimpleNamespace

from aiohttp import web
import pytest

from custom_components.hacs.brands import HacsBrandIconView
from custom_components.hacs.const import BRAND_ICON_CDN_URL
from custom_components.hacs.enums import HacsCategory


class FakeHass:
    """Minimal Home Assistant test double."""

    async def async_add_executor_job(self, target, *args):
        """Run executor jobs inline for the unit test."""
        return target(*args)


def _repository(*, category=HacsCategory.INTEGRATION, domain="example", local_path=None):
    """Build a minimal HACS repository test double."""
    return SimpleNamespace(
        data=SimpleNamespace(category=category, domain=domain),
        content=SimpleNamespace(path=SimpleNamespace(local=local_path)),
    )


async def test_brand_icon_view_serves_installed_integration_icon(tmp_path):
    """Test local brand icons are served for installed integrations."""
    brand_dir = tmp_path / "brand"
    brand_dir.mkdir()
    (brand_dir / "icon.png").write_bytes(b"icon")

    hacs = SimpleNamespace(
        repositories=SimpleNamespace(
            list_downloaded=[_repository(domain="example", local_path=str(tmp_path))]
        )
    )
    view = HacsBrandIconView(FakeHass(), hacs)

    response = await view.get(None, "example")

    assert response.body == b"icon"
    assert response.content_type == "image/png"


async def test_brand_icon_view_falls_back_to_cdn_for_missing_icon(tmp_path):
    """Test missing local icons redirect to the existing CDN fallback."""
    hacs = SimpleNamespace(
        repositories=SimpleNamespace(
            list_downloaded=[_repository(domain="example", local_path=str(tmp_path))]
        )
    )
    view = HacsBrandIconView(FakeHass(), hacs)

    with pytest.raises(web.HTTPFound) as err:
        await view.get(None, "example")

    assert err.value.location == BRAND_ICON_CDN_URL.format(domain="example")


async def test_brand_icon_view_rejects_invalid_domain():
    """Test invalid domains are not redirected."""
    hacs = SimpleNamespace(repositories=SimpleNamespace(list_downloaded=[]))
    view = HacsBrandIconView(FakeHass(), hacs)

    response = await view.get(None, "../example")

    assert response.status == 404
