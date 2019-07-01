"""Serve HacsSettingsView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from homeassistant.const import __version__ as HAVERSION

from ...blueprints import HacsViewBase
from ...const import ISSUE_URL, NAME_LONG, ELEMENT_TYPES, VERSION

_LOGGER = logging.getLogger("custom_components.hacs.frontend")


class HacsSettingsView(HacsViewBase):
    """Serve HacsSettingsView."""

    name = "community_settings"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["settings"]

    async def get(self, request):
        """Serve HacsOverviewView."""
        try:
            # We use these later:
            repository_lines = []
            hidden = []
            hacs = self.store.repositories.get("172733314")

            if hacs is None:
                return web.Response(
                    body=self.base_content, content_type="text/html", charset="utf-8"
                )

            # Get the message sendt to us:
            message = request.rel_url.query.get("message")
            if message is None:
                if VERSION == "DEV":
                    message = "You are running a DEV version of HACS, this is not intended for regular use."

            if message != None:
                custom_message = """
                    <div class='container'>
                        <div class="row">
                            <div class="col s12">
                                <div class="card-panel orange darken-4">
                                    <div class="card-content white-text">
                                        <span>
                                            {}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                """.format(
                    message
                )
            else:
                custom_message = ""

            pending = ""
            # Repos:
            if not self.store.task_running:
                for repository in self.repositories_list_repo:
                    if repository.pending_update:
                        pending += "<p>- {} ({} -> {})</p></br>".format(
                            repository.name,
                            repository.version_installed
                            if repository.version_installed is not None
                            else repository.installed_commit,
                            repository.last_release_tag
                            if repository.last_release_tag is not None
                            else repository.last_commit,
                        )

                    if repository.hide and repository.repository_id != "172733314":
                        line = '<li class="collection-item hacscolor hacslist"><div>'
                        line += """
                            <a href="{}/repository_unhide/{}">
                            <i title="Unhide" class="fas fa-plus-circle" style="padding-right: 8px"></i></a> 
                            {}
                            <span class="repository-list-badge">{}</span>
                        """.format(
                            self.url_path["api"],
                            repository.repository_id,
                            repository.repository_name,
                            repository.repository_type,
                        )
                        line += "</div></li>"
                        hidden.append(line)

                    if not repository.custom:
                        continue

                    line = '<li class="collection-item hacscolor hacslist"><div>'
                    line += """
                        <a href="{}/{}"><span class="repository-list-badge">{}</span> {}</a> 
                    """.format(
                        self.url_path["repository"],
                        repository.repository_id,
                        repository.repository_type,
                        repository.repository_name,
                    )

                    if repository.installed:
                        remove = """
                            <i title="Remove is not possible when {} is installed." class="secondary-content fas fa-trash-alt disabledaction"></i>
                        """.format(
                            repository.repository_type
                        )
                    else:
                        remove = """
                            <a href={}/repository_remove/{} onclick="toggleLoading()" class="secondary-content" style="color: var(--primary-color)">
                                <i title="Remove." class="fas fa-trash-alt"></i>
                            </a>
                        """.format(
                            self.url_path["api"], repository.repository_id
                        )
                    line += remove
                    line += "</div></li>"

                    repository_lines.append(line)

            # Generate content to display
            content = self.base_content
            content += """
                <div class='hacs-overview-container'>
                    {}
                </div>
            """.format(
                custom_message
            )

            # HACS card
            types = ["Grid", "Table"]
            selected = self.store.frontend_mode
            if selected is None:
                selected = "Grid"
            if selected in types:
                types.remove(selected)
            overview_display = """
                <form action="{}/frontend/view" name="overview_display"
                        method="post" accept-charset="utf-8"
                        enctype="application/x-www-form-urlencoded"
                        class="hacs-form">
                    <select name="view_type" class="hacs-select" onchange="document.getElementsByName('overview_display')[0].submit()">
                        <option class="hacscolor" value="{selected}">{selected}</option>
                        <option class="hacscolor" value="{option}">{option}</option>
                    </select>
                </form>
            """.format(
                self.url_path["api"], selected=selected, option=types[0]
            )
            content += """
                <div class='hacs-overview-container'>
                    <div class="hacs-card-standalone">
                        <h5>{}</h5>
                        <b>HACS version:</b> {}{}</br>
                        <b>Home Assistant version:</b> {}</br>
                        </br>
                        <b>Display:</b> {}
                    </div>
                </div>
            """.format(
                NAME_LONG,
                hacs.version_installed,
                " <b>(RESTART PENDING!)</b>" if hacs.pending_restart else "",
                HAVERSION,
                overview_display,
            )

            # The buttons, must have buttons
            modal1 = """
                <div id="modal1" class="modal hacscolor">
                    <div class="modal-content">
                    <h5>Pending Upgrades</h5>
                    {}
                    <p>Be carefull using this feature, elements may contain breaking changes,
                    make sure you read the release notes for all the elements in the list above.</p>
                    </div>
                    <div class="modal-footer hacscolor">
                        {}
                        <a {} href="{}/repositories_upgrade_all/notinuse"  onclick="toggleLoading()" class='waves-effect waves-light btn hacsbutton' style="background-color: var(--google-red-500) !important; font-weight: bold;">
                            UPGRADE ALL
                        </a>
                    </div>
                </div>
            """.format(
                pending,
                "<p>Background task is running, upgrade is disabled.</p>"
                if self.store.task_running
                else "",
                "style='display: none'" if self.store.task_running else "",
                self.url_path["api"],
            )

            upgrade_all_btn = """
                <a class="waves-effect waves-light btn modal-trigger hacsbutton" href="#modal1" style="background-color: var(--google-red-500) !important; font-weight: bold;">UPGRADE ALL</a>
            """

            if pending == "":
                upgrade_all_btn = ""

            content += """
                {}
                <div class='hacs-overview-container'>
                    <a href="{}/repositories_reload/notinuse" class='waves-effect waves-light btn hacsbutton' onclick="toggleLoading()">
                        RELOAD DATA
                    </a>
                    {}
                    <a href='{}/new/choose' class='waves-effect waves-light btn right hacsbutton' target="_blank">
                        OPEN ISSUE
                    </a>
                    <a rel='noreferrer' href='https://github.com/custom-components/hacs' class='waves-effect waves-light btn right hacsbutton' target="_blank">
                        HACS REPO
                    </a>
                </div>
            """.format(
                modal1, self.url_path["api"], upgrade_all_btn, ISSUE_URL
            )

            ## Integration URL's
            content += """
                <div class='hacs-overview-container'>
                    <div class="row">
                        <ul class="collection with-header hacslist">
                            <li class="collection-header hacscolor hacslist"><h5>CUSTOM REPOSITORIES</h5></li>
            """
            for line in repository_lines:
                content += line

            element_types = ""
            for element_type in sorted(ELEMENT_TYPES):
                element_types += "<option class='hacscolor' value='{}'>{}</option>".format(
                    element_type, element_type.title()
                )

            content += """
                        </ul>
                        <form action="{}/repository_register/new" 
                                method="post" accept-charset="utf-8"
                                enctype="application/x-www-form-urlencoded">
                            <input id="custom_url" type="text" name="custom_url" 
                                    placeholder="ADD CUSTOM REPOSITORY" style="width: 70%; color: var(--primary-text-color)">

                            <select name="repository_type" class="hacs-select">
                                <option disabled selected value>type</option>
                                {}
                            </select>

                            <button class="btn waves-effect waves-light right" 
                                    type="submit" name="add" onclick="toggleLoading()" style="background-color: var(--primary-color); height: 44px;">
                                <i class="fas fa-save"></i>
                            </button>
                        </form>
                    </div>
                </div>
            """.format(
                self.url_path["api"], element_types
            )

            ## Hidden repositories
            if hidden:
                content += """
                    <div class='hacs-overview-container'>
                        <div class="row">
                            <ul class="collection with-header hacslist">
                                <li class="collection-header hacscolor hacslist"><h5>HIDDEN REPOSITORIES</h5></li>
                """
                for line in sorted(hidden):
                    content += line
                content += """
                            </ul>
                        </div>
                    </div>
                """

            content += self.footer

        except Exception as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

        return web.Response(body=content, content_type="text/html", charset="utf-8")
