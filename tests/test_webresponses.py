import pytest

from custom_components.hacs.webresponses.frontend import HacsFrontendDev
from tests.common import BaseDummySession, BaseMockResponse


class DummySession(BaseDummySession):
    async def get(self, path):
        if path == "/entrypoint.js":
            return BaseMockResponse()
        return BaseMockResponse(status=400)


@pytest.mark.asyncio
async def test_frontend(hacs):
    hacs.session = DummySession()
    view = HacsFrontendDev()

    response = await view.get(None, "entrypoint.js")
    assert response.status == 200
    assert response.headers["Content-Type"] == "application/javascript"

    response = await view.get(None, "other.js")
    assert response is None
