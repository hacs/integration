"""Test the repository brand icon view."""

from collections.abc import Generator
import os
from unittest.mock import MagicMock

from aiohttp import web
from aiohttp.test_utils import make_mocked_request
from homeassistant.core import HomeAssistant
import pytest

from custom_components.hacs.brands import MAX_ICON_SIZE, PNG_MAGIC, HacsRepositoryIconView
from custom_components.hacs.const import DOMAIN

from tests.common import MockedResponse, ResponseMocker, get_hacs

REPOSITORY_ID = "1296269"
REPOSITORY_FULL_NAME = "hacs-test-org/integration-basic"
ICON_CONTENT = PNG_MAGIC + b"icon-content"
DARK_ICON_CONTENT = PNG_MAGIC + b"dark-icon-content"
ACCESS_TOKEN = "test-token"
RAW_ICON_URL = (
    "https://raw.githubusercontent.com/hacs-test-org/integration-basic"
    "/1.0.0/custom_components/example/brand/icon.png"
)
RAW_DARK_ICON_URL = (
    "https://raw.githubusercontent.com/hacs-test-org/integration-basic"
    "/1.0.0/custom_components/example/brand/dark_icon.png"
)


async def _get_icon(
    hass: HomeAssistant,
    repository_id: str,
    filename: str,
    *,
    authenticated: bool = True,
    view: HacsRepositoryIconView | None = None,
) -> web.StreamResponse:
    view = view or HacsRepositoryIconView(hass)
    url = f"/api/hacs/repository/{repository_id}/{filename}"
    if authenticated:
        hass.data["brands"] = (ACCESS_TOKEN,)
        url = f"{url}?token={ACCESS_TOKEN}"
    request = make_mocked_request("GET", url)
    return await view.get(request, repository_id=repository_id, filename=filename)


async def test_icon_view_requires_authentication(
    hass: HomeAssistant,
) -> None:
    """Test that unauthenticated icon requests are rejected."""
    with pytest.raises(web.HTTPForbidden):
        await _get_icon(hass, REPOSITORY_ID, "icon.png", authenticated=False)


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
    assert response.headers["Location"] == (
        f"/api/hacs/repository/{REPOSITORY_ID}/icon.png?token={ACCESS_TOKEN}"
    )


async def test_icon_view_remote_error_is_not_cached(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
) -> None:
    """Test that transient download errors are retried on the next request."""
    response_mocker.add(RAW_ICON_URL, MockedResponse(status=500))

    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 302
    assert response.headers["Cache-Control"] == "no-store"
    marker_file = hass.config.path(".storage/hacs.icons/1296269-1.0.0-icon.png.missing")
    assert not os.path.exists(marker_file)

    response_mocker.add(RAW_ICON_URL, MockedResponse(content=ICON_CONTENT))
    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 200
    assert response.body == ICON_CONTENT


async def test_icon_view_remote_icon_size_limit(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
) -> None:
    """Test that oversized remote icons are rejected while streaming."""
    response_mocker.add(
        RAW_ICON_URL,
        MockedResponse(content=PNG_MAGIC + bytes(MAX_ICON_SIZE)),
    )

    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 302
    marker_file = hass.config.path(".storage/hacs.icons/1296269-1.0.0-icon.png.missing")
    assert os.path.exists(marker_file)


async def test_icon_view_remote_content_in_root(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
) -> None:
    """Test loading an icon from a repository with content in its root."""
    repository = get_hacs(hass).repositories.get_by_full_name(REPOSITORY_FULL_NAME)
    repository.repository_manifest.content_in_root = True
    response_mocker.add(
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/1.0.0/brand/icon.png",
        MockedResponse(content=ICON_CONTENT),
    )

    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 200
    assert response.body == ICON_CONTENT


async def test_icon_view_remote_branch_cache_uses_commit(
    hass: HomeAssistant,
    setup_integration: Generator,
    response_mocker: ResponseMocker,
) -> None:
    """Test refreshing cached branch icons when the latest commit changes."""
    repository = get_hacs(hass).repositories.get_by_full_name(REPOSITORY_FULL_NAME)
    repository.data.last_version = None
    repository.data.default_branch = "main"
    repository.data.last_commit = "abc1234"
    url = (
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic"
        "/main/custom_components/example/brand/icon.png"
    )
    response_mocker.add(url, MockedResponse(content=ICON_CONTENT))

    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 200
    assert os.path.exists(hass.config.path(".storage/hacs.icons/1296269-abc1234-icon.png"))

    repository.data.last_commit = "def5678"
    response_mocker.add(url, MockedResponse(content=DARK_ICON_CONTENT))
    response = await _get_icon(hass, REPOSITORY_ID, "icon.png")

    assert response.status == 200
    assert response.body == DARK_ICON_CONTENT


async def test_icon_view_uses_current_hacs_instance(
    hass: HomeAssistant,
) -> None:
    """Test that a registered view follows the HACS instance across reloads."""
    view = HacsRepositoryIconView(hass)
    replacement_hacs = MagicMock()
    replacement_hacs.repositories.get_by_id.return_value = None
    hass.data[DOMAIN] = replacement_hacs

    with pytest.raises(web.HTTPNotFound):
        await _get_icon(hass, REPOSITORY_ID, "icon.png", view=view)

    replacement_hacs.repositories.get_by_id.assert_called_once_with(REPOSITORY_ID)


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
    assert response.headers["Location"] == (
        f"/api/hacs/repository/{REPOSITORY_ID}/icon.png?token={ACCESS_TOKEN}"
    )


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
