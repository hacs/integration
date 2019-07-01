"""Serve HacsStoreView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from ...blueprints import HacsViewBase
from ...const import ELEMENT_TYPES
from ...repositoryinformation import RepositoryInformation

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

            if not self.store.repositories:
                content += "Loading store items, check back later."

            else:

                content += """
                    <div class='hacs-overview-container'>
                        <input type="text" id="Search" onkeyup="Search()" placeholder="Please enter a search term.." title="Type in a name" autofocus style="color: var(--primary-text-color)">
                    </div>
                """

                for repository in self.repositories_list_name:
                    repository = RepositoryInformation(self.store.repositories[repository.repository_id])

                    if (
                        not repository.track
                        or repository.hide
                        or repository.repository_id == "172733314"
                    ):
                        continue

                    card_icon = "<i class='fas fa-cube card-status {}'></i>".format(repository.status)
                    badge = '<span class="repository-list-badge hacs-table-badge">NEW</span>' if repository.new else ''

                    if self.store.frontend_mode == "Table":
                        badge = '<span class="repository-list-badge hacs-table-badge">NEW</span>' if repository.new else ''
                        card = self.load_element("repository/row_store")
                        card = card.replace("{ICON}", card_icon.replace("<i", "<i style='margin-left: 25%'"))

                    else:
                        badge = '<span class="repository-list-badge hacs-grid-badge">NEW</span>' if repository.new else ''
                        card = self.load_element("repository/card_store")
                        card = card.replace("{ICON}", card_icon)

                    card = card.replace("{INSTALLED}", repository.installed_version)
                    card = card.replace("{AVAILABLE}", repository.available_version)
                    card = card.replace("{API}", self.url_path["repository"])
                    card = card.replace("{ID}", repository.repository_id)
                    card = card.replace("{NAME}", repository.name)
                    card = card.replace("{BADGE}", badge)
                    card = card.replace("{TOPICS}", repository.topics)
                    card = card.replace("{AUTHORS}", repository.authors)
                    card = card.replace("{REPOSITORY_NAME}", repository.repository_name)
                    card = card.replace("{DESCRIPTION}", repository.description)

                    types[repository.repository_type].append(card)


                for element_type in sorted(ELEMENT_TYPES):
                    if types[element_type]:
                        typedisplay = "{}S".format(element_type.upper())
                        if element_type == "appdaemon":
                            typedisplay = "APPDAEMON APPS"
                        elif element_type == "python_script":
                            typedisplay = "PYTHON SCRIPTS"
                        if self.store.frontend_mode == "Table":
                            rows = ""
                            for card in types[element_type]:
                                rows += card
                            table = self.load_element("overview/table")
                            table = table.replace('<th class="smal-hide">Installed</th>', "")
                            table = table.replace('<th class="smal-hide">Available</th>', "")
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
                    content = self.base_content
                    content += "Loading store items, check back later."

                content += self.footer

        except SystemError as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

        return web.Response(body=content, content_type="text/html", charset="utf-8")
