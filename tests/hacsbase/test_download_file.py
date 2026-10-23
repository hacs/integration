# pylint: disable=missing-module-docstring, missing-function-docstring
"""Downloads must always give their connection back to the session's pool."""

from unittest.mock import AsyncMock, MagicMock, patch


class _Response:
    def __init__(self, status: int, body: bytes = b"", headers: dict | None = None):
        self.status = status
        self.headers = headers or {}
        self._body = body
        self.released = False

    async def read(self) -> bytes:
        return self._body

    def release(self) -> None:
        self.released = True


class _Request:
    """Like aiohttp's request context manager: awaitable, or usable with `async with`."""

    def __init__(self, response: _Response):
        self.response = response

    def __await__(self):
        async def _get() -> _Response:
            return self.response

        return _get().__await__()

    async def __aenter__(self) -> _Response:
        return self.response

    async def __aexit__(self, *_) -> None:
        self.response.release()

    @property
    def released(self) -> bool:
        return self.response.released


def _session(*responses: _Response) -> tuple[MagicMock, list[_Request]]:
    requests = [_Request(response) for response in responses]
    session = MagicMock()
    session.get = MagicMock(side_effect=requests)
    return session, requests


async def test_download_releases_the_connection_on_success(hacs, monkeypatch):
    session, requests = _session(_Response(200, b"content"))
    monkeypatch.setattr(hacs, "session", session)

    assert await hacs.async_download_file("https://example.test/file.js") == b"content"
    assert all(request.released for request in requests)


async def test_download_releases_the_connection_on_an_error_status(hacs, monkeypatch):
    session, requests = _session(_Response(404))
    monkeypatch.setattr(hacs, "session", session)

    assert await hacs.async_download_file("https://example.test/file.js", nolog=True) is None
    assert all(request.released for request in requests)


async def test_download_releases_the_connection_when_retrying_a_rate_limit(hacs, monkeypatch):
    session, requests = _session(
        _Response(429, headers={"retry-after": "1"}),
        _Response(200, b"content"),
    )
    monkeypatch.setattr(hacs, "session", session)

    with patch("custom_components.hacs.base.asyncio.sleep", new=AsyncMock()):
        result = await hacs.async_download_file(
            "https://example.test/file.js", handle_rate_limit=True
        )

    assert result == b"content"
    assert len(requests) == 2
    assert all(request.released for request in requests)
