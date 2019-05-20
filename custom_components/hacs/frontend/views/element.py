"""CommunityAPI View for HACS."""
import logging
from aiohttp import web
from homeassistant.components.http import HomeAssistantView

from custom_components.hacs.const import DOMAIN_DATA
from custom_components.hacs.frontend.views import error_view
from custom_components.hacs.frontend.elements import style, header, Generate

_LOGGER = logging.getLogger(__name__)


class CommunityElement(HomeAssistantView):
    """View to serve the overview."""

    requires_auth = False

    url = r"/community_element/{path}"
    name = "community_element"

    def __init__(self, hass):
        """Initialize overview."""
        self.hass = hass
        self.element = None
        self.generate = None

    async def get(self, request, path):  # pylint: disable=unused-argument
        """View to serve the overview."""
        _LOGGER.debug("Trying to serve %s", path)

        try:
            html = await self.element_view(path)

        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error("Ups... There was an isse generating the page %s", error)
            html = await error_view()

        # Show the content
        return web.Response(body=html, content_type="text/html", charset="utf-8")

    async def element_view(self, element):
        """element_view."""
        _LOGGER.debug("Trying to generate view for %s", element)

        self.element = self.hass.data[DOMAIN_DATA]["elements"][element]
        self.generate = Generate(self.hass, self.element)

        content_style = await style()
        content_header = await header()
        main_content = await self.element_view_content()

        return """
          {content_style}
          {content_header}
          <div class='container''>
            {main_content}
          </div>
        """.format(
            content_style=content_style,
            content_header=content_header,
            main_content=main_content,
        )

    async def element_view_content(self):
        """Generate the content for a single element."""

        # Generate objects
        authors = await self.generate.authors()
        avaiable_version = await self.generate.avaiable_version()
        changelog = await self.generate.changelog()
        description = await self.generate.description()
        element_note = await self.generate.element_note()
        example_config = await self.generate.example_config()
        example_image = await self.generate.example_image()
        installed_version = await self.generate.installed_version()
        main_action = await self.generate.main_action()
        name = self.element.name
        repo = await self.generate.repo()
        restart_pending = await self.generate.restart_pending()
        uninstall = await self.generate.uninstall()

        content = """
          {restart_pending}
          <div class="row">
            <div class="col s12">
              <div class="card blue-grey darken-1">
                <div class="card-content white-text">
                  <span class="card-title">{name}</span>
                  {description}
                  {installed_version}
                  {avaiable_version}
                  {example_image}
                  {example_config}
                  </br>
                  {authors}
                  {element_note}
                </div>
                <div class="card-action">
                  {main_action}
                  {changelog}
                  {repo}
                  {uninstall}
                </div>
              </div>
            </div>
          </div>
        """.format(
            authors=authors,
            avaiable_version=avaiable_version,
            changelog=changelog,
            description=description,
            element_note=element_note,
            example_config=example_config,
            example_image=example_image,
            installed_version=installed_version,
            main_action=main_action,
            name=name,
            repo=repo,
            restart_pending=restart_pending,
            uninstall=uninstall,
        )

        return content
