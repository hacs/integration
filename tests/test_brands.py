"""Test the repository brand icon view."""

from collections.abc import Generator
import os

from aiohttp import web
from aiohttp.test_utils import make_mocked_request
from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.brands import PNG_MAGIC, HacsRepositoryIconView

from tests.common import MockedResponse, ResponseMocker, get_hacs

REPOSITORY_ID = "1296269"
REPOSITORY_FULL_NAME = "hacs-test-org/integration-basic"
ICON_CONTENT = PNG_MAGIC + b"icon-content"
DARK_ICON_CONTENT = PNG_MAGIC + b"dark-icon-content"
RAW_ICON_URL = (
    "https://raw.githubusercontent.com/hacs-test-org/integration-basic"
    "/1.0.0/custom_components/example/brand/icon.png"
)
RAW_DARK_ICON_URL = (
    "https://raw.githubusercontent.com/hacs-test-org/integration-basic"
    "/1.0.0/custom_components/example/brand/dark_icon.png"
)


async def _get_icon(hass: HomeAssistant, repository_id: str, filename: str) -> web.StreamResponse:
    view = HacsRepositoryIconView(get_hacs(hass))
    request = make_mocked_request("GET", f"/api/hacs/repository/{repository_id}/{filename}")
    return await view.get(request, repository_id=repository_id, filename=filename)


@pytest.mark.parametrize(
    ("repository_id", "filename"),
    [
        (REPOSITORY_ID, "not_an_icon.png"),
        (REPOSITORY_ID, "../icon.png"),
        ("0000000", "icon.png"),
    ],
)
async def test_icon_view_not_found(
    hass: HomeAssistant,
    setup_integration: Generator,
    repository_id: str,
    filename: str,
) -> None:
    """Test that unknown repositories and unexpected filenames return 404."""
    with pytest.raises(web.HTTPNotFound):
        await _get_icon(hass, repository_id, filename)


async def test_icon_view_remote_icon(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
) -> None:
    """Test serving the icon of a repository that is not downloaded."""
    response_mocker.add(RAW_ICON_URL, MockedResponse(content=ICON_CONTENT))

    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 200
    assert response.body == ICON_CONTENT
    assert response.content_type == "image/png"
    assert "max-age" in response.headers["Cache-Control"]

    cache_file = hass.config.path(".storage/hacs.icons/1296269-1.0.0-icon.png")
    assert os.path.exists(cache_file)

    # A second request is served from the cache without hitting GitHub again,
    # the mocked response was consumed by the first request.
    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")
    assert response.status == 200
    assert response.body == ICON_CONTENT


async def test_icon_view_remote_icon_missing(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
) -> None:
    """Test redirecting to the brands CDN when the repository has no icon."""
    response_mocker.add(RAW_ICON_URL, MockedResponse(status=404))

    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 302
    assert response.headers["Location"] == "https://brands.home-assistant.io/_/example/icon.png"

    marker_file = hass.config.path(".storage/hacs.icons/1296269-1.0.0-icon.png.missing")
    assert os.path.exists(marker_file)

    # The negative result is cached, GitHub is not asked again.
    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")
    assert response.status == 302


async def test_icon_view_remote_icon_invalid_content(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
) -> None:
    """Test that content that is not a PNG image is not served."""
    response_mocker.add(RAW_ICON_URL, MockedResponse(content=b"not a png"))

    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 302
    assert response.headers["Location"] == "https://brands.home-assistant.io/_/example/icon.png"


async def test_icon_view_remote_dark_icon_fallback(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
) -> None:
    """Test redirecting to the regular icon when there is no dark variant."""
    response_mocker.add(RAW_DARK_ICON_URL, MockedResponse(status=404))

    response = await _get_icon(hass, REPOSITORY_ID, "dark_icon.png")

    assert response.status == 302
    assert response.headers["Location"] == f"/api/hacs/repository/{REPOSITORY_ID}/icon.png"


async def test_icon_view_downloaded_icon(
    hass: HomeAssistant,
    setup_integration: Generator,
) -> None:
    """Test serving the local icon of a downloaded repository."""
    hacs = get_hacs(hass)
    repository = hacs.repositories.get_by_full_name(REPOSITORY_FULL_NAME)
    repository.data.installed = True

    brand_dir = hass.config.path("custom_components/example/brand")

    def _write_icon() -> None:
        os.makedirs(brand_dir, exist_ok=True)
        with open(os.path.join(brand_dir, "icon.png"), mode="wb") as icon_file:
            icon_file.write(ICON_CONTENT)

    await hass.async_add_executor_job(_write_icon)

    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 200
    assert response.body == ICON_CONTENT

    # The dark variant does not exist, redirect to the regular icon.
    response = await _get_icon(hass, REPOSITORY_ID, "dark_icon.png")

    assert response.status == 302
    assert response.headers["Location"] == f"/api/hacs/repository/{REPOSITORY_ID}/icon.png"


async def test_icon_view_downloaded_icon_invalid_content(
    hass: HomeAssistant,
    setup_integration: Generator,
) -> None:
    """Test that a local file that is not a PNG image is not served."""
    hacs = get_hacs(hass)
    repository = hacs.repositories.get_by_full_name(REPOSITORY_FULL_NAME)
    repository.data.installed = True

    brand_dir = hass.config.path("custom_components/example/brand")

    def _write_icon() -> None:
        os.makedirs(brand_dir, exist_ok=True)
        with open(os.path.join(brand_dir, "icon.png"), mode="wb") as icon_file:
            icon_file.write(b"not a png")

    await hass.async_add_executor_job(_write_icon)

    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 302
    assert response.headers["Location"] == "https://brands.home-assistant.io/_/example/icon.png"


async def test_icon_view_downloaded_icon_missing(
    hass: HomeAssistant,
    setup_integration: Generator,
) -> None:
    """Test redirecting to the brands CDN when the download has no brand folder."""
    hacs = get_hacs(hass)
    repository = hacs.repositories.get_by_full_name(REPOSITORY_FULL_NAME)
    repository.data.installed = True

    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 302
    assert response.headers["Location"] == "https://brands.home-assistant.io/_/example/icon.png"
