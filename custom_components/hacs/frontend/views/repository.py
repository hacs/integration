"""Serve HacsRepositoryView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from ...blueprints import HacsViewBase

_LOGGER = logging.getLogger("custom_components.hacs.frontend")

LOVELACE_EXAMLE_URL = """
<pre id="LovelaceExample" class="yaml">
  - url: /community_plugin/{}/{}.js
</pre>
"""

MISSING_JS_TYPE = """
<i>HACS could not determine the type of this element, look at the documentation in the repository.</i></br>
"""

LOVELACE_EXAMLE_URL_TYPE = """
<pre id="LovelaceExample" class="yaml">
  - url: /community_plugin/{}/{}.js
    type: {}
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
            repository = self.repositories[str(repository_id)]

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

            if repository.pending_restart:
                pending_restart = """
                    <div class='container''>
                        <div class="row">
                            <div class="col s12">
                                <div class="card-panel orange darken-4">
                                    <div class="card-content white-text">
                                        <span>
                                            You need to restart (and potentially reconfigure) Home Assistant, for your last operation to be loaded.
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
                if repository.info is None:
                    info = "</br>" + await self.aiogithub.render_markdown(
                        repository.additional_info
                    )
                    info = info.replace("<h3>", "<h6>").replace("</h3>", "</h6>")
                    info = info.replace("<h2>", "<h5>").replace("</h2>", "</h5>")
                    info = info.replace("<h1>", "<h4>").replace("</h1>", "</h4>")
                    info = info.replace("<code>", "<code class='codeinfo'>")
                    info = info.replace(
                        '<a href="http',
                        '<a rel="noreferrer" target="_blank" href="http',
                    )
                    info = info.replace("<ul>", "")
                    info = info.replace("</ul>", "")
                    repository.info = info
                else:
                    info = repository.info
            else:
                info = ""

            if repository.authors:
                if repository.repository_type == "integration":
                    authors = "<p>Author(s): "
                    for author in repository.authors:
                        if "@" in author:
                            author = author.split("@")[-1]
                        authors += "<a rel='noreferrer' href='https://github.com/{author}' target='_blank' style='color: var(--primary-color) !important; margin: 2'> @{author}</a>".format(
                            author=author
                        )
                    authors += "</p>"
                else:
                    authors = "<p>Author: {}</p>".format(repository.authors)
            else:
                authors = ""

            if (
                repository.repository_type == "integration"
                and repository.repository_id != "172733314"
            ):
                note = """
                    </br>
                    <i>
                        When installed, this will be located in '{}',
                        you still need to add it to your 'configuration.yaml' file.
                    </i>
                """.format(
                    repository.local_path
                )
            elif repository.repository_type == "plugin":
                if repository.javascript_type is None:
                    llnote = LOVELACE_EXAMLE_URL.format(
                        repository.name, repository.name.replace("lovelace-", "")
                    )
                    jsnote = MISSING_JS_TYPE
                else:
                    llnote = LOVELACE_EXAMLE_URL_TYPE.format(
                        repository.name,
                        repository.name.replace("lovelace-", ""),
                        repository.javascript_type,
                    )
                    jsnote = ""
                note = """
                    </br><i>
                        When installed, this will be located in '{}',
                        you still need to add it to your lovelace configuration ('ui-lovelace.yaml' or the raw UI config editor).
                    </i>
                    </br></br>
                    <i>
                        When you add this to your configuration use this:
                    </i></br>
                        {}
                    <a title="Copy content to clipboard" id ="lovelacecopy" onclick="CopyToLovelaceExampleToClipboard()"><i class="fa fa-copy"></i></a>
                    {}
                """.format(
                    repository.local_path, llnote, jsnote
                )
            elif repository.repository_type == "appdaemon":
                note = """
                    </br>
                    <i>
                        When installed, this will be located in '{}',
                        you still need to add it to your 'apps.yaml' file.
                    </i>
                """.format(
                    repository.local_path
                )
            else:
                note = ""

            note += """
                    </br></br><i>
                        To learn more about how to configure this,
                        click the "REPOSITORY" link below button to get to the repository for this {}.
                    </i>
            """.format(
                "AppDaemon app"
                if repository.repository_type == "appdaemon"
                else repository.repository_type
            )

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
                    open_plugin = "<a href='/community_plugin/{}/{}.js' target='_blank' style='color: var(--primary-color) !important'>OPEN PLUGIN</a>".format(
                        repository.name, name
                    )
            else:
                open_plugin = ""

            # Hide/unhide
            if repository.installed or repository.custom:
                hide_option = ""
            else:
                if repository.hide:
                    hide_option = """
                        <li><a class="dropdown-list-item" href="{}/repository_unhide/{}" onclick="ShowProgressBar()">Unhide</a></li>
                    """.format(
                        self.url_path["api"], repository.repository_id
                    )
                else:
                    hide_option = """
                        <li><a class="dropdown-list-item" href="{}/repository_hide/{}" onclick="ShowProgressBar()">Hide</a></li>
                    """.format(
                        self.url_path["api"], repository.repository_id
                    )

            # Beta
            if repository.last_release_tag is not None:
                show_beta = '<li><a class="dropdown-list-item" href="{}/repository_{}_beta/{}" onclick="ShowProgressBar()">{}</a></li>'
                if repository.show_beta:
                    show_beta = show_beta.format(
                        self.url_path["api"],
                        "hide",
                        repository.repository_id,
                        "Hide Beta",
                    )
                else:
                    show_beta = show_beta.format(
                        self.url_path["api"],
                        "show",
                        repository.repository_id,
                        "Show Beta",
                    )
            else:
                show_beta = ""

            content = self.base_content

            if repository.version_installed is not None:
                inst_ver = "<p><b>Installed version:</b> {}</p>".format(
                    repository.version_installed
                )
            else:
                if repository.installed_commit is not None:
                    inst_ver = "<p><b>Installed commit:</b> {}</p>".format(
                        repository.installed_commit
                    )
                else:
                    inst_ver = ""

            if repository.last_release_tag is not None:
                last_ver = "<p><b>Available version:</b> {}</p>".format(
                    repository.last_release_tag
                )
            else:
                last_ver = "<p><b>Available commit:</b> {}</p>".format(
                    repository.last_commit
                )

            last_up = ""

            if repository.pending_update and repository.version_installed is not None:
                changelog = "<a rel='noreferrer' href='https://github.com/{}/releases/{}' target='_blank' style='color: var(--primary-color) !important'>CHANGELOG</a>".format(
                    repository.repository_name, repository.ref.replace("/tags", "")
                )
            else:
                changelog = ""

            if repository.installed and repository.repository_id != "172733314":
                uninstall = "<a href='{}/repository_uninstall/{}' style='float: right; color: var(--google-red-500) !important; font-weight: bold;' onclick='ShowProgressBar()'>UNINSTALL</a>".format(
                    self.url_path["api"], repository.repository_id
                )
            else:
                uninstall = ""

            content += """
                {}
                {}
                <div class='hacs-overview-container'>
                    <div class="row">
                        <div class="col s12">
                            <div class="card hacscolor">
                                <div class="card-content">
                                    <span class="card-title">
                                        <b>{}</b>

                                        <a class='dropdown-trigger btn right' href='#' data-target='dropdown1' style="background-color: var(--primary-color); padding-top: 8px; height: 48">
                                            <i class="fas fa-bars"></i>
                                        </a>

                                        <ul id='dropdown1' class='dropdown-content'>
                                            <li><a class="dropdown-list-item" href="{}/repository_update_repository/{}" onclick="ShowProgressBar()">Reload</a></li>
                                            {}
                                            {}
                                            <li><a class="dropdown-list-item" rel='noreferrer' href="https://github.com/{}/issues/" target="_blank">Open a issue</a></li>
                                            <li><a class="dropdown-list-item" rel='noreferrer' href="https://github.com/custom-components/hacs/issues/new?title={}&labels=flag&assignee=ludeeus&template=flag.md" target="_blank">Flag this</a></li>
                                        </ul>
                                    </span>
                                    <p>{}</p></br>
                                    {}
                                    {}
                                    {}
                                    <span>{}</span>
                                    </br>
                                    {}
                                    {}
                                </div>
                                <div class="card-action">
                                    <a href="{}/repository_install/{}"
                                        onclick="ShowProgressBar()" style='color: var(--primary-color) !important'>
                                        {}
                                    </a>
                                    {}
                                    <a rel='noreferrer' href='https://github.com/{}' target='_blank' style='color: var(--primary-color) !important'>repository</a>
                                    {}
                                    {}
                                </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            """.format(
                custom_message,
                pending_restart,
                repository.name
                if repository.repository_type == "integration"
                else repository.name.replace("-", " ").replace("_", " ").title(),
                self.url_path["api"],
                repository.repository_id,
                show_beta,
                hide_option,
                repository.repository_name,
                repository.name,
                repository.description,
                inst_ver,
                last_ver,
                last_up,
                info,
                authors,
                note,
                self.url_path["api"],
                repository.repository_id,
                main_action,
                changelog,
                repository.repository_name,
                open_plugin,
                uninstall,
            )

        except Exception as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

        return web.Response(body=content, content_type="text/html", charset="utf-8")
