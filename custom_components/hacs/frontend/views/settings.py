"""CommunityAPI View for HACS."""
import logging
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.const import __version__ as HAVERSION

from custom_components.hacs.const import DOMAIN_DATA, NAME_LONG, VERSION
from custom_components.hacs.frontend.views import error_view
from custom_components.hacs.frontend.elements import (
    info_card,
    style,
    header,
    generic_button_external,
    generic_button_local,
    warning_card,
)

_LOGGER = logging.getLogger(__name__)


class CommunitySettings(HomeAssistantView):
    """View to serve the overview."""
    # TODO: Add reload button to the left of the repo names to reload single custom repo

    requires_auth = False

    url = r"/community_settings"
    name = "community_settings"

    def __init__(self, hass):
        """Initialize overview."""
        self.hass = hass
        self.message = None

    async def get(self, request):  # pylint: disable=unused-argument
        """View to serve the overview."""
        self.message = request.rel_url.query.get("message")
        try:
            html = await self.settings_view()
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error(error)
            html = await error_view()
        return web.Response(body=html, content_type="text/html", charset="utf-8")

    async def settings_view(self):
        """Settings view."""
        content = ""
        content += await style()
        content += await header()

        content += "<div class='container'>"

        if self.hass.data[DOMAIN_DATA]["hacs"].get("pending_restart"):
            content += await warning_card(
                "You need to restart Home Assisant to start using the latest version of HACS."
            )

        if (
            self.hass.data[DOMAIN_DATA]["hacs"]["local"]
            != self.hass.data[DOMAIN_DATA]["hacs"]["remote"]
        ):
            content += """
                <div class="row">
                    <div class="col s12">
                    <div class="card  red darken-4">
                        <div class="card-content white-text">
                        <span class="card-title">UPDATE PENDING</span>
                        <p>There is an update pending for HACS!.</p>
                        </br>
                        <p>Current version: {}</p>
                        <p>Available version: {}</p>
                        </div>
                        <div class="card-action">
                        <a href="/community_api/hacs/upgrade"
                            onclick="document.getElementById('progressbar').style.display = 'block'">
                            UPGRADE</a>
                        </div>
                    </div>
                    </div>
                </div>
            """.format(
                self.hass.data[DOMAIN_DATA]["hacs"]["local"],
                self.hass.data[DOMAIN_DATA]["hacs"]["remote"],
            )

        # Show info message
        if self.message is not None and self.message != "None":
            content += await warning_card(self.message)

        # Integration URL's
        content += """
        <div class="row">
                <ul class="collection with-header">
                    <li class="collection-header"><h5>CUSTOM INTEGRATION REPO'S</h5></li>
        """
        if self.hass.data[DOMAIN_DATA]["repos"].get("integration"):
            for entry in self.hass.data[DOMAIN_DATA]["repos"].get("integration"):
                content += """
                    <li class="collection-item">
                        <div>{}
                            <a href="/community_api/integration_url_delete/{}" class="secondary-content">
                                <i name="delete" class="fas fa-trash-alt"></i>
                            </a>
                        </div>
                    </li>
                """.format(
                    entry, entry.replace("/", "%2F")
                )
        content += """
                </ul>
            <form action="/community_api/integration_url/add" method="post" accept-charset="utf-8" enctype="application/x-www-form-urlencoded">
                <input id="custom_url" type="text" name="custom_url" placeholder="ADD CUSTOM INTEGRATION REPO" style="width: 90%">
                    <button class="btn waves-effect waves-light right" type="submit" name="add" onclick="document.getElementById('progressbar').style.display = 'block'">
                        <i class="fas fa-save"></i>
                    </button>
            </form> 
            </br>
        """

        # Plugin URL's
        content += """
                <ul class="collection with-header">
                    <li class="collection-header"><h5>CUSTOM PLUGIN REPO'S</h5></li>
        """
        if self.hass.data[DOMAIN_DATA]["repos"].get("plugin"):
            for entry in self.hass.data[DOMAIN_DATA]["repos"].get("plugin"):
                content += """
                    <li class="collection-item">
                        <div>{}
                            <a href="/community_api/plugin_url_delete/{}" class="secondary-content">
                                <i name="delete" class="fas fa-trash-alt"></i>
                            </a>
                        </div>
                    </li>
                """.format(
                    entry, entry.replace("/", "%2F")
                )
        content += """
                </ul>
            <form action="/community_api/plugin_url/add" method="post" accept-charset="utf-8" enctype="application/x-www-form-urlencoded">
                <input id="custom_url" type="text" name="custom_url" placeholder="ADD CUSTOM PLUGIN REPO" style="width: 90%">
                    <button class="btn waves-effect waves-light right" type="submit" name="add" onclick="document.getElementById('progressbar').style.display = 'block'">
                        <i class="fas fa-save"></i>
                    </button>
            </form> 
        </div>
        """

        content += "</br>"
        content += "</br>"
        content += await generic_button_local(
            "/community_api/self/reload", "RELOAD DATA"
        )
        content += await generic_button_external(
            "https://github.com/custom-components/hacs/issues/new", "OPEN ISSUE"
        )
        content += await generic_button_external(
            "https://github.com/custom-components/hacs", "HACS REPO"
        )
        content += await generic_button_external("/community_api/log/get", "OPEN LOG")
        content += "</br>"
        content += "</br>"
        info_message = """
        <h5>{}</h5>
        <b>HACS version:</b> {}</br>
        <b>Home Assistant version:</b> {}</br>
        </br>
        <i>
            <a href="https://www.buymeacoffee.com/ludeeus" target="_blank" style="font-weight: 700;">
                Built while consuming (a lot of) <i class="fas fa-beer" style="font-weight: 700;"></i>
            </a>
        </i>
        </br>
        <hr>
        <h6>UI built with elements from:</h6>
        <li><a href="https://materializecss.com" target="_blank" style="font-weight: 700;">Materialize</a></li>
        <li><a href="https://fontawesome.com" target="_blank" style=";font-weight: 700;">Font Awesome</a></li>
        <hr>
        <i>This site and the items here is not created, developed, affiliated, supported, maintained or endorsed by Home Assistant.</i>
        """.format(
            NAME_LONG, VERSION, HAVERSION
        )
        content += await info_card(info_message)
        content += "</div>"  # End the view container
        return content
