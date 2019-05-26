"""Serve HacsRepositoryView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from custom_components.hacs.blueprints import HacsViewBase

_LOGGER = logging.getLogger('custom_components.hacs.frontend')

LOVELACE_EXAMLE_URL = """
resources:
  - url: /community_plugin/{}
"""
LOVELACE_EXAMLE_URL_TYPE = """
resources:
  - url: /community_plugin/{}
    type: {}
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
                                        <a href="{self.url_path["api"]}/repository_update/{repository.repository_id}"
                                                style="float: right; color: #ffab40;" onclick="ShowProgressBar()">
                                            <i name="reload" class="fa fa-sync"></i>
                                        </a>
                                    </span>
                                    <p>{repository.description}</p></br>
                                    {f"<p><b>Installed version:</b> {repository.version_installed}</p>" if repository.version_installed is not None else ""}
                                    {f"<p><b>Available version:</b> {repository.last_release_tag}</p>" if repository.last_release_tag is not None else ""}
                                    {f"<p><b>Last updated:</b> {repository.last_updated}</p>" if repository.last_updated is not None else ""}
                                    {"info"}
                                    </br>
                                    {"authors"}
                                    {"element_note"}
                                </div>
                                <div class="card-action">
                                    {"main_action"}
                                    {"changelog"}
                                    {"repo"}
                                    {"open_plugin"}
                                    {"uninstall"}
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