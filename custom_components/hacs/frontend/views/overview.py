"""CommunityAPI View for HACS."""
import logging
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from custom_components.hacs.const import DOMAIN_DATA, NO_ELEMENTS
from custom_components.hacs.frontend.views import error_view
from custom_components.hacs.frontend.elements import style, header, cards, Generate

_LOGGER = logging.getLogger(__name__)


class CommunityOverview(HomeAssistantView):
    """View to serve the overview."""

    requires_auth = False

    url = r"/community_overview"
    name = "community_overview"

    def __init__(self, hass):
        """Initialize overview."""
        self.hass = hass

    async def get(self, request):  # pylint: disable=unused-argument
        """View to serve the overview."""
        _LOGGER.debug("Trying to serve overview")
        try:
            html = await self.content()
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error(error)
            html = await error_view()
        return web.Response(body=html, content_type="text/html", charset="utf-8")

    async def content(self):
        """Content."""
        content = ""

        content += await style()
        content += await header()

        content += "<div class='container''>"
        content += "<h5>CUSTOM INTEGRATIONS</h5>"
        content += await overview(self.hass, "integration", True)
        content += "<h5>CUSTOM PLUGINS (LOVELACE)</h5>"
        content += await overview(self.hass, "plugin", True)
        content += "</div>"

        return content


async def overview(hass, element_type, show_installed_only=False):
    """Overview."""
    content = ""
    elements = []
    if not hass.data[DOMAIN_DATA]["elements"]:
        return NO_ELEMENTS
    for entry in hass.data[DOMAIN_DATA]["elements"]:
        element = hass.data[DOMAIN_DATA]["elements"][entry]
        if show_installed_only:
            if not element.isinstalled:
                continue
        if element.element_type == element_type:
            elements.append(element)
    if not elements:
        return NO_ELEMENTS
    else:
        for element in elements:
            card_icon = await Generate(hass, element).card_icon()
            content += await cards.overview_card(element, card_icon)
        return content
