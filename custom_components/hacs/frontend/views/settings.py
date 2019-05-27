"""Serve HacsSettingsView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from homeassistant.const import __version__ as HAVERSION

from custom_components.hacs.blueprints import HacsViewBase
from custom_components.hacs.const import ISSUE_URL, NAME_LONG

_LOGGER = logging.getLogger('custom_components.hacs.frontend')


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
            integrations = []
            plugins = []

            # Get the message sendt to us:
            message = request.rel_url.query.get("message")

            # HACS restart pending
            if self.data["hacs"].get("pending_restart"):
                hacs_restart = f"""
                    <div class='container'>
                        <div class="row">
                            <div class="col s12">
                                <div class="card-panel orange darken-4">
                                    <div class="card-content white-text">
                                        <span>
                                            You need to restart Home Assisant to start using the latest version of HACS.
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                """
            else:
                hacs_restart = ""

            # HACS update pending
            if self.data["hacs"]["local"] != self.data["hacs"]["remote"]:
                hacs_update = f"""
                    <div class='container'>
                        <div class="row">
                            <div class="col s12">
                                <div class="card  red darken-4">
                                    <div class="card-content white-text">
                                        <span class="card-title">UPDATE PENDING</span>

                                        <p>There is an update pending for HACS!.</p>
                                        </br>
                                        <p><b>Current version:</b> {self.data["hacs"]["local"]}</p>
                                        <p><b>Available version:</b> {self.data["hacs"]["remote"]}</p>
                                    </div>

                                    <div class="card-action">
                                        <a href="{self.url_path["api"]}/hacs/upgrade" onclick="ShowProgressBar()">UPGRADE</a>
                                        <a href="https://github.com/custom-components/hacs/releases/tag/{self.data["hacs"]["remote"]}" target="_blank">CHANGELOG</a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                """
            else:
                hacs_update = ""

            if message != None:
                custom_message = f"""
                    <div class='container'>
                        <div class="row">
                            <div class="col s12">
                                <div class="card-panel orange darken-4">
                                    <div class="card-content white-text">
                                        <span>
                                            {message}
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                """
            else:
                custom_message = ""


            # Repos:
            for repository in self.repositories:
                repository = self.repositories[repository]
                if not repository.custom:
                    continue

                line = '<li class="collection-item"><div>'
                line += """
                    <a title="Reload data." href="{}/repository_update/{}" onclick="ShowProgressBar()">
                    <i class="fa fa-sync" style="color: #26a69a; margin-right: 1%"></i></a> 
                """.format(self.url_path["api"], repository.repository_id)
                line += repository.repository_name

                if repository.installed:
                    remove = """
                        <i title="Remove is not possible when {} is installed." class="secondary-content fas fa-trash-alt disabledaction"></i>
                    """.format(repository.repository_type)
                else:
                    remove = """
                        <a href={} onclick="ShowProgressBar()" class="secondary-content">
                            <i title="Remove." class="fas fa-trash-alt"></i>
                        </a>
                    """.format(self.url_path["api"])
                line += remove
                line += "</div></li>"


                if repository.repository_type == "integration":
                    integrations.append(line)

                elif repository.repository_type == "plugin":
                    plugins.append(line)





            # Generate content to display
            content = self.base_content
            content += f"""
                <div class='container'>
                    {hacs_restart}
                    {hacs_update}
                    {custom_message}
                </div>
            """

            ## Integration URL's
            content += """
                <div class='container'>
                    <div class="row">
                        <ul class="collection with-header">
                            <li class="collection-header"><h5>CUSTOM INTEGRATION REPO'S</h5></li>
            """
            for line in integrations:
                content += line
            content += f"""
                        </ul>
                        <form action="{self.url_path["api"]}/repository_register/integration" 
                                method="post" accept-charset="utf-8"
                                enctype="application/x-www-form-urlencoded">
                            <input id="custom_url" type="text" name="custom_url" 
                                    placeholder="ADD CUSTOM INTEGRATION REPO" style="width: 90%">
                                <button class="btn waves-effect waves-light right" 
                                        type="submit" name="add" onclick="ShowProgressBar()">
                                    <i class="fas fa-save"></i>
                                </button>
                        </form>
                    </div>
                </div>
            """

            ## Plugin URL's
            content += """
                <div class='container'>
                    <div class="row">
                        <ul class="collection with-header">
                            <li class="collection-header"><h5>CUSTOM PLUGIN REPO'S</h5></li>
            """
            for line in plugins:
                content += line
            content += f"""
                        </ul>
                        <form action="{self.url_path["api"]}/repository_register/plugin" 
                                method="post" accept-charset="utf-8"
                                enctype="application/x-www-form-urlencoded">
                            <input id="custom_url" type="text" name="custom_url" 
                                    placeholder="ADD CUSTOM PLUGIN REPO" style="width: 90%">
                                <button class="btn waves-effect waves-light right" 
                                        type="submit" name="add" onclick="ShowProgressBar()">
                                    <i class="fas fa-save"></i>
                                </button>
                        </form>
                    </div>
                </div>
            """

            # The buttons, must have buttons
            content += f"""
                <div class='container' style="padding-right: 2%">
                    <a href="{self.url_path["api"]}/self/reload" class='waves-effect waves-light btn hacsbutton' onclick="ShowProgressBar()">
                        RELOAD DATA
                    </a>
                    <a href='{ISSUE_URL}/new/choose' class='waves-effect waves-light btn right hacsbutton' target="_blank">
                        OPEN ISSUE
                    </a>
                    <a href='https://github.com/custom-components/hacs' class='waves-effect waves-light btn right hacsbutton' target="_blank">
                        HACS REPO
                    </a>
                    <a href="{self.url_path["api"]}/log/get" class='waves-effect waves-light btn right hacsbutton' onclick="ShowProgressBar()">
                        OPEN LOG
                    </a>
                </div>
            """

            # Bottom card
            content += f"""
                <div class='container'>
                    <div class="row">
                        <div class="col s12">
                            <div class="card-panel" style="background-color: #bbdefb00 !important">
                                <div class="card-content black-text">
                                    <h5>{NAME_LONG}</h5>
                                    <b>HACS version:</b> {self.data["hacs"]["local"]}
                                    {" <b>(RESTART PENDING!)</b>" if self.data["hacs"].get("pending_restart") else ""}</br>
                                    <b>Home Assistant version:</b> {HAVERSION}</br>
                                    </br>
                                    <hr>
                                    <h6>UI built with elements from:</h6>
                                    <li><a href="https://materializecss.com" target="_blank" style="font-weight: 700;">Materialize</a></li>
                                    <li><a href="https://fontawesome.com" target="_blank" style=";font-weight: 700;">Font Awesome</a></li>
                                    <hr>
                                    <i>This site and the items here is not created, developed, affiliated, supported, maintained or endorsed by Home Assistant.</i>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            """

        except Exception as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

        return web.Response(body=content, content_type="text/html", charset="utf-8")
