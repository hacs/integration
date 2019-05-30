"""Serve HacsRepositoryView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from custom_components.hacs.blueprints import HacsViewBase

_LOGGER = logging.getLogger('custom_components.hacs.frontend')

LOVELACE_EXAMLE_URL = """
<pre id="LovelaceExample" class="yaml">
  - url: /community_plugin/{name}/{name}.js
</pre>
"""
LOVELACE_EXAMLE_URL_TYPE = """
<pre id="LovelaceExample" class="yaml">
  - url: /community_plugin/{name}/{name}.js
    type: {type}
</pre>
"""

class HacsRepositoryView(HacsViewBase):
    """Serve HacsRepositoryView."""

    name = "community_repository"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["repository"] + r"/{repository_id}"

    async def get(self, request, repository_id):
        """Serve HacsRepositoryView."""
        try:
            message = request.rel_url.query.get("message")
            repository = self.repositories[repository_id]

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


            if repository.pending_restart:
                pending_restart = f"""
                    <div class='container''>
                        <div class="row">
                            <div class="col s12">
                                <div class="card-panel orange darken-4">
                                    <div class="card-content white-text">
                                        <span>
                                            You need to restart Home Assisant, for your last operation to be loaded.
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                """
            else:
                pending_restart = ""

            if repository.additional_info:
                info = "</br>" + await self.aiogithub.render_markdown(repository.additional_info)
                info = info.replace("<h3>", "<h6>").replace(
                    "</h3>", "</h6>"
                )
                info = info.replace("<h2>", "<h5>").replace(
                    "</h2>", "</h5>"
                )
                info = info.replace("<h1>", "<h4>").replace(
                    "</h1>", "</h4>"
                )
                info = info.replace("<code>", "<pre>").replace(
                    "</code>", "</pre>"
                )
                info = info.replace(
                    "<table>", "<table class='white-text'>"
                )
                info = info.replace("<ul>", "")
                info = info.replace("</ul>", "")
            else:
                info = ""


            if repository.authors:
                authors = "<p>Author(s): "
                for author in repository.authors:
                    if "@" in author:
                        author = author.split("@")[-1]
                    authors += f"<a href='https://github.com/{author}' target='_blank' style='margin: 2'> @{author}</a>"
                authors += "</p>"
            else:
                authors = ""

            if repository.repository_type == "integration":
                note = f"""
                    </br>
                    <i>
                        When installed, this will be located in '{repository.local_path}',
                        you still need to add it to your 'configuration.yaml' file.
                    </i></br></br>
                    <i>
                        To learn more about how to configure this,
                        click the "REPO" button to get to the repoistory for this integration.
                    </i>
                """
            else:
                note = f"""
                    </br><i>
                        When installed, this will be located in '{repository.local_path}',
                        you still need to add it to your lovelace configuration ('ui-lovelace.yaml' or the raw UI config editor).
                    </i>
                    </br></br>
                    <i>
                        When you add this to your configuration use this:
                    </i></br>
                        {
                            LOVELACE_EXAMLE_URL.format(name=repository.name)
                            if repository.javascript_type is None else
                            LOVELACE_EXAMLE_URL_TYPE.format(name=repository.name, type=repository.javascript_type)
                        }
                    <a title="Copy content to clipboard" id ="lovelacecopy" onclick="CopyToLovelaceExampleToClipboard()"><i class="fa fa-copy"></i></a>
                    </br></br><i>
                        To learn more about how to configure this,
                        click the "REPO" button to get to the repoistory for this plugin.
                    </i>
                """

            if not repository.installed:
                main_action = "INSTALL"
            elif repository.pending_update:
                main_action = "UPGRADE"
            else:
                main_action = "REINSTALL"

            if repository.repository_type == "plugin":
                if not repository.installed:
                    open_plugin = ""
                else:
                    if "lovelace-" in repository.name:
                        name = repository.name.split("lovelace-")[-1]
                    else:
                        name = repository.name
                    open_plugin = f"<a href='/community_plugin/{repository.name}/{name}.js' target='_blank'>OPEN PLUGIN</a>"
            else:
                open_plugin = ""

            # Generate content
            content = self.base_content

            content += f"""
                {custom_message}
                {pending_restart}
                <div class='container''>
                    <div class="row">
                        <div class="col s12">
                            <div class="card blue-grey darken-1">
                                <div class="card-content white-text">
                                    <span class="card-title">
                                        {repository.name}
                                        <a href="{self.url_path["api"]}/repository_update_repository/{repository.repository_id}"
                                                style="float: right; color: #ffab40;" onclick="ShowProgressBar()">
                                            <i name="reload" class="fa fa-sync"></i>
                                        </a>
                                    </span>
                                    <p>{repository.description}</p></br>
                                    {f"<p><b>Installed version:</b> {repository.version_installed}</p>" if repository.version_installed is not None else ""}
                                    {f"<p><b>Available version:</b> {repository.last_release_tag}</p>" if repository.last_release_tag is not None else ""}
                                    {f"<p><b>Last updated:</b> {repository.last_updated}</p>" if repository.last_updated is not None else ""}
                                    <span>{info}</span>
                                    </br>
                                    {authors}
                                    {note}
                                </div>
                                <div class="card-action">
                                    <a href="{self.url_path["api"]}/repository_install/{repository.repository_id}"
                                        onclick="ShowProgressBar()">
                                        {main_action}
                                    </a>
                                    {
                                        f"<a href='https://github.com/{repository.repository_name}/releases' target='_blank'>CHANGELOG</a>"
                                        if repository.pending_update else ""
                                    }
                                    <a href='https://github.com/{repository.repository_name}' target='_blank'>repository</a>
                                    {open_plugin}
                                    {
                                        f"<a href='{self.url_path['api']}/repository_uninstall/{repository.repository_id}' style='float: right; color: #a70000; font-weight: bold;' onclick='ShowProgressBar()'>UNINSTALL</a>"
                                        if repository.installed else ""
                                    }
                                </div>
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