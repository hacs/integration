"""Serve HacsOverviewView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from ...blueprints import HacsViewBase
from ...const import NO_ELEMENTS, ELEMENT_TYPES

_LOGGER = logging.getLogger("custom_components.hacs.frontend")


class HacsOverviewView(HacsViewBase):
    """Serve HacsOverviewView."""

    name = "community_overview"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["overview"]

    async def get(self, request):  # pylint: disable=unused-argument
        """Serve HacsOverviewView."""
        try:
            content = self.base_content

            types = {}
            for element_type in ELEMENT_TYPES:
                types[element_type] = []

            if not self.repositories:
                if not self.data["task_running"]:
                    content += NO_ELEMENTS

            else:
                for repository in self.repositories_list_name:

                    if (
                        not repository.track
                        or repository.hide
                        or not repository.installed
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

                    card = """
                    <a href="{}/{}" class="hacs-card"">
                        <div class="hacs-card overview">
                            <meta topics="{}">
                            <meta repository_authors="{}">
                            <meta name="{}">
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
                        content += "<div class='hacs-overview-container'>"
                        typedisplay = "{}S".format(element_type.upper())
                        if element_type == "appdaemon":
                            typedisplay = "APPDAEMON APPS"
                        content += "<h5>{}</h5>".format(typedisplay)
                        content += "<div class='hacs-card-container'>"
                        for card in types[element_type]:
                            content += card
                        content += "</div></div>"

                if not types:
                    if not self.data["task_running"]:
                        content += NO_ELEMENTS

                content += self.footer

        except Exception as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

        return web.Response(body=content, content_type="text/html", charset="utf-8")
