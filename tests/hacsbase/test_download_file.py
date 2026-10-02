"""Download URLs must retain real Git refs and file paths."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hacs.base import HacsBase


@pytest.mark.parametrize("keep_url", [False, True])
@pytest.mark.parametrize(
    "url",
    [
        "https://raw.githubusercontent.com/owner/repo/fix-release-tags/hacs.json",
        "https://raw.githubusercontent.com/owner/repo/feature/tags/foo/hacs.json",
        "https://raw.githubusercontent.com/owner/tags/main/hacs.json",
        "https://raw.githubusercontent.com/tags/repo/main/hacs.json",
        "https://raw.githubusercontent.com/owner/repo/main/docs/tags/example.md",
        "https://raw.githubusercontent.com/owner/repo/tags/v1.0.0/hacs.json",
        "https://raw.githubusercontent.com/owner/repo/refs/tags/v1.0.0/hacs.json",
        "https://github.com/owner/repo/archive/refs/tags/v1.0.0.zip",
        "https://github.com/owner/repo/releases/download/tags/v1.0.0/example.zip",
    ],
)
async def test_download_preserves_url(url: str, keep_url: bool) -> None:
    """Pass complete download URLs to the HTTP client unchanged."""
    hacs = HacsBase()
    response = MagicMock(status=200, read=AsyncMock(return_value=b"download"))
    hacs.session = MagicMock(get=AsyncMock(return_value=response))

    assert await hacs.async_download_file(url, keep_url=keep_url) == b"download"

    assert hacs.session.get.await_count == 1
    assert hacs.session.get.call_args.kwargs["url"] == url
