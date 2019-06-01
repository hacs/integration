"""Serve HacsStoreView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from custom_components.hacs.blueprints import HacsViewBase

_LOGGER = logging.getLogger('custom_components.hacs.frontend')


class HacsStoreView(HacsViewBase):
    """Serve HacsOverviewView."""

    name = "community_store"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["store"]

    async def get(self, request):  # pylint: disable=unused-argument
        """Serve HacsStoreView."""
        try:
            content = self.base_content

            integrations = []
            plugins = []

            if not self.repositories:
                content += "Loading store items, check back later."

            else:

                content += """
                    <div class='container'>
                        <input type="text" id="Search" onkeyup="Search()" placeholder="Please enter a search term.." title="Type in a name" autofocus>
                    </div>
                """


                for repository in self.repositories:
                    repository = self.repositories[repository]

                    if not repository.track or repository.hide:
                        continue

                    if repository.pending_restart:
                        card_icon = "<i class='fas fa-info right' style='font-size: 18px; color: #a70000'></i>"

                    elif repository.installed and repository.pending_update:
                        card_icon = "<i class='fas fa-arrow-up right' style='font-size: 18px; color: #ffab40'></i>"

                    else:
                        card_icon = ""

                    card = """
                        <div class="row">
                            <div class="col s12">
                                <div class="card blue-grey darken-1">
                                    <div class="card-content white-text">
                                        <meta topics="{}">
                                        <meta repository_authors="{}">
                                        <span class="card-title">
                                            {} {}
                                        </span>
                                        <span class="white-text">
                                            <p>{}</p>
                                        </span>
                                    </div>
                                    <div class="card-action">
                                        <a href="{}/{}">
                                            {}
                                        </a>
                                    </div>
                                </div>
                            </div>
                        </div>
                        """.format(repository.topics, repository.authors, repository.name, card_icon, repository.description, self.url_path["repository"], repository.repository_id, "MANAGE" if repository.installed else "MORE INFO")

                    if repository.repository_type == "integration":
                        integrations.append(card)

                    elif repository.repository_type == "plugin":
                        plugins.append(card)

                    else:
                        continue

                if integrations:
                    content += "<div class='container'>"
                    content += "<h5>CUSTOM INTEGRATIONS</h5>"
                    for card in integrations:
                        content += card
                    content += "</div>"

                if plugins:
                    content += "<div class='container'>"
                    content += "<h5>CUSTOM PLUGINS (LOVELACE)</h5>"
                    for card in plugins:
                        content += card
                    content += "</div>"

                if not plugins and not integrations:
                    content = self.base_content
                    content += "Loading store items, check back later."

        except SystemError as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

        return web.Response(body=content, content_type="text/html", charset="utf-8")
