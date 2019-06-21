"""Serve HacsStoreView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from ...blueprints import HacsViewBase
from ...const import ELEMENT_TYPES

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

            types = {}
            for element_type in ELEMENT_TYPES:
                types[element_type] = []

            if not self.repositories:
                content += "Loading store items, check back later."

            else:

                content += """
                    <div class='hacs-overview-container'>
                        <input type="text" id="Search" onkeyup="Search()" placeholder="Please enter a search term.." title="Type in a name" autofocus style="color: var(--primary-text-color)">
                    </div>
                """

                for repository in self.repositories_list_name:

                    if (
                        not repository.track
                        or repository.hide
                        or repository.repository_id == "172733314"
                    ):
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

                    if self.data.get("hacs", {}).get("view") == "Table":
                        card = """
                            <tr class="hacs-table-row" onclick="window.location='{}/{}';">
                                <!--{}-->
                                <!--{}-->
                                <!--{}-->
                                <td>{}</td>
                                <td>{}</td>
                                <td class="hacs-card-content smal-hide">{}</td>
                            </tr>
                        """.format(
                            self.url_path["repository"],
                            repository.repository_id,
                            repository.topics,
                            repository.authors,
                            repository.name,
                            card_icon.replace("<i", "<i style='margin-left: 25%'"),
                            repository.name
                            if repository.repository_type == "integration"
                            else repository.name.replace("-", " ")
                            .replace("_", " ")
                            .title(),
                            repository.description,
                        )
                        card += "</div></li>"

                    else:

                        card = """
                        <a href="{}/{}" class="hacs-card"">
                            <div class="hacs-card overview">
                                <!--{}-->
                                <!--{}-->
                                <!--{}-->
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
                            repository.name,
                            card_icon,
                            repository.name
                            if repository.repository_type == "integration"
                            else repository.name.replace("-", " ")
                            .replace("_", " ")
                            .title(),
                            repository.description,
                        )

                    types[repository.repository_type].append(card)

                for element_type in sorted(ELEMENT_TYPES):
                    if types[element_type]:
                        typedisplay = "{}S".format(element_type.upper())
                        if element_type == "appdaemon":
                            typedisplay = "APPDAEMON APPS"
                        elif element_type == "python_script":
                            typedisplay = "PYTHON SCRIPTS"
                        if self.data.get("hacs", {}).get("view") == "Table":
                            content += """
                            <div class='hacs-overview-container'>
                                <div class="row">
                                    <h5>{}</h5>
                                    <table class="hacs-table">
                                        <thead>
                                            <tr>
                                                <th>Status</th>
                                                <th>Name</th>
                                                <th class="smal-hide">Description</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                            """.format(
                                typedisplay
                            )
                            for card in types[element_type]:
                                content += card
                            content += """
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                            """
                        else:
                            content += "<div class='hacs-overview-container'>"
                            content += "<h5>{}</h5>".format(typedisplay)
                            content += "<div class='hacs-card-container'>"
                            for card in types[element_type]:
                                content += card
                            content += "</div></div></br></br>"

                if not types:
                    content = self.base_content
                    content += "Loading store items, check back later."

                content += self.footer

        except SystemError as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

        return web.Response(body=content, content_type="text/html", charset="utf-8")
