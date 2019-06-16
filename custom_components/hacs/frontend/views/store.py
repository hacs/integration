"""Serve HacsStoreView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from ...blueprints import HacsViewBase

_LOGGER = logging.getLogger("custom_components.hacs.frontend")


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
                    <div class='hacs-overview-container'>
                        <input type="text" id="Search" onkeyup="Search()" placeholder="Please enter a search term.." title="Type in a name" autofocus style="color: var(--primary-text-color)">
                    </div>
                """

                for repository in self.repositories_list_name:

                    if not repository.track or repository.hide:
                        continue

                    if repository.pending_restart:
                        card_icon = (
                            "<i class='fas fa-cube card-status pending-restart'></i>"
                        )

                    elif repository.pending_update:
                        card_icon = (
                            "<i class='fas fa-cube card-status pending-update'></i>"
                        )

                    elif repository.installed:
                        card_icon = "<i class='fas fa-cube card-status installed'></i>"

                    else:
                        card_icon = "<i class='fas fa-cube card-status default'></i>"

                    card = """
                    <a href="{}/{}" class="hacs-card"">
                        <div class="hacs-card overview">
                            <meta topics="{}">
                            <meta repository_authors="{}">
                            <span class="hacs-card-title">{} {}</span>
                            <span class="hacs-card-content">
                                <p>{}</p>
                            </span>
                        </div>
                    </a>
                    """.format(
                        self.url_path["repository"],
                        repository.repository_id,
                        repository.topics,
                        repository.authors,
                        card_icon,
                        repository.name,
                        repository.description,
                    )

                    if repository.repository_type == "integration":
                        integrations.append(card)

                    elif repository.repository_type == "plugin":
                        plugins.append(card)

                    else:
                        continue

                if integrations:
                    content += "<div class='hacs-overview-container'>"
                    content += "<h5>CUSTOM INTEGRATIONS</h5>"
                    content += "<div class='hacs-card-container'>"
                    for card in integrations:
                        content += card
                    content += "</div></div>"

                if plugins:
                    content += "<div class='hacs-overview-container'>"
                    content += "<h5>CUSTOM PLUGINS (LOVELACE)</h5>"
                    content += "<div class='hacs-card-container'>"
                    for card in plugins:
                        content += card
                    content += "</div></div>"

                if not plugins and not integrations:
                    content = self.base_content
                    content += "Loading store items, check back later."

                content += self.footer

        except SystemError as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

        return web.Response(body=content, content_type="text/html", charset="utf-8")
