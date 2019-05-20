"""CommunityAPI View for HACS."""
import logging
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from custom_components.hacs.frontend.views import error_view
from custom_components.hacs.frontend.views.overview import overview
from custom_components.hacs.frontend.elements import style, header


_LOGGER = logging.getLogger(__name__)


class CommunityStore(HomeAssistantView):
    """View to serve the overview."""

    requires_auth = False

    url = r"/community_store"
    name = "community_store"

    def __init__(self, hass):
        """Initialize overview."""
        self.hass = hass

    async def get(self, request):  # pylint: disable=unused-argument
        """View to serve the overview."""
        try:
            html = await self.store_view()
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error(error)
            html = await error_view()
        return web.Response(body=html, content_type="text/html", charset="utf-8")

    async def store_view(self):
        """element_view."""
        content = ""
        content += await style()
        content += await header()
        content += """
        <script>
            function Search() {
            var input = document.getElementById("Search");
            var filter = input.value.toLowerCase();
            var nodes = document.getElementsByClassName('row');

            for (i = 0; i < nodes.length; i++) {
                if (nodes[i].innerText.toLowerCase().includes(filter)) {
                nodes[i].style.display = "block";
                } else {
                nodes[i].style.display = "none";
                }
            }
            }
        </script>
        """
        content += "<div class='container''>"
        content += '<input type="text" id="Search" onkeyup="Search()" placeholder="Please enter a search term.." title="Type in a name">'
        content += "<h5>CUSTOM INTEGRATIONS</h5>"
        content += await overview(self.hass, "integration")
        content += "<h5>CUSTOM PLUGINS (LOVELACE)</h5>"
        content += await overview(self.hass, "plugin")
        content += "</div>"
        return content
