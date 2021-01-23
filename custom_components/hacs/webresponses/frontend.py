from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from custom_components.hacs.share import get_hacs


class HacsFrontendDev(HomeAssistantView):
    """Dev View Class for HACS."""

    requires_auth = False
    name = "hacs_files:frontend"
    url = r"/hacsfiles/frontend/{requested_file:.+}"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Handle HACS Web requests."""
        hacs = get_hacs()
        requested = requested_file.split("/")[-1]
        request = await hacs.session.get(
            f"{hacs.configuration.frontend_repo_url}/{requested}"
        )
        if request.status == 200:
            result = await request.read()
            response = web.Response(body=result)
            response.headers["Content-Type"] = "application/javascript"

            return response
