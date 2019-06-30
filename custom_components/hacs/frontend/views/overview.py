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

            if not self.store.repositories:
                if not self.data["task_running"]:
                    content += NO_ELEMENTS

            else:
                for repository in self.store.repositories:
                    repository = self.store.repositories[repository]

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

                    if self.data.get("hacs", {}).get("view") == "Table":
                        if repository.repository_type == "integration":
                            name = repository.name
                        else:
                            name = repository.name.replace("-", " ").replace("_", " ").title()

                        if repository.version_installed:
                            installed = repository.version_installed
                        else:
                            if repository.installed_commit:
                                installed = repository.version_installed
                            else:
                                installed = ""

                        if repository.last_release_tag:
                            available = repository.last_release_tag
                        else:
                            available = repository.last_commit

                        card = self.load_element("repository/row_overview")
                        card = card.replace("{API}", self.url_path["repository"])
                        card = card.replace("{ID}", repository.repository_id)
                        card = card.replace("{ICON}", card_icon.replace("<i", "<i style='margin-left: 25%'"))
                        card = card.replace("{NAME}", name)
                        card = card.replace("{DESCRIPTION}", repository.description)
                        card = card.replace("{INSTALLED}", installed)
                        card = card.replace("{AVAILABLE}", available)

                    else:
                        if repository.repository_type == "integration":
                            name = repository.name
                        else:
                            name = repository.name.replace("-", " ").replace("_", " ").title()

                        card = self.load_element("repository/card")
                        card = card.replace("{API}", self.url_path["repository"])
                        card = card.replace("{ID}", repository.repository_id)
                        card = card.replace("{ICON}", card_icon)
                        card = card.replace("{NAME}", name)
                        card = card.replace("{DESCRIPTION}", repository.description)

                    types[repository.repository_type].append(card)

                for element_type in sorted(ELEMENT_TYPES):
                    if types[element_type]:
                        typedisplay = "{}S".format(element_type.upper())
                        if element_type == "appdaemon":
                            typedisplay = "APPDAEMON APPS"
                        elif element_type == "python_script":
                            typedisplay = "PYTHON SCRIPTS"
                        if self.data.get("hacs", {}).get("view") == "Table":
                            rows = ""
                            for card in types[element_type]:
                                rows += card
                            table = self.load_element("overview/table")
                            table = table.replace("{TYPE}", typedisplay)
                            table = table.replace("{ROWS}", rows)
                            content += table

                        else:
                            cards = ""
                            for card in types[element_type]:
                                cards += card
                            grid = self.load_element("overview/grid")
                            grid = grid.replace("{TYPE}", typedisplay)
                            grid = grid.replace("{CARDS}", cards)
                            content += grid


                if not types:
                    if not self.data["task_running"]:
                        content += NO_ELEMENTS

                content += self.footer

        except Exception as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

        return web.Response(body=content, content_type="text/html", charset="utf-8")
