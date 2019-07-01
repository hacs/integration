"""Serve HacsRepositoryView."""
# pylint: disable=broad-except
import logging
from aiohttp import web
from packaging.version import Version
from homeassistant.const import __version__ as HAVERSION

from ...blueprints import HacsViewBase
from ...const import NOT_SUPPORTED_HA_VERSION
from ...repositoryinformationview import RepositoryInformationView

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
            repository = self.store.repositories[str(repository_id)]
            if not repository.updated_info:
                await repository.set_repository()
                await repository.update()
                repository.updated_info = True
                await self.storage.set()

            if repository.new:
                repository.new = False
                await self.storage.set()

            repository = RepositoryInformationView(repository)
            content = self.base_content

            if message != None:
                content += self.load_element("custom_message").replace("{MESSAGE}", message)

            if repository.status == "pending-restart":
                content += self.load_element("repository/pending_restart")


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
                        repository.full_name, repository.full_name.replace("lovelace-", "")
                    )
                    jsnote = MISSING_JS_TYPE
                else:
                    llnote = LOVELACE_EXAMLE_URL_TYPE.format(
                        repository.full_name,
                        repository.full_name.replace("lovelace-", ""),
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
                        click the "REPOSITORY" link button to get to the repository for this {}.
                    </i>
            """.format(
                "AppDaemon app"
                if repository.repository_type == "appdaemon"
                else repository.repository_type
            )

            main_action = """
                <a href="{}/repository_install/{}"
                    onclick="toggleLoading()" style='color: var(--primary-color) !important'>
                    {}
                </a>
            """.format(
                    self.url_path["api"], repository.repository_id, repository.main_action
                )

            if repository.repository_type == "plugin":
                if not repository.installed:
                    open_plugin = ""
                else:
                    if "lovelace-" in repository.full_name:
                        name = repository.full_name.split("lovelace-")[-1]
                    else:
                        name = repository.full_name
                    open_plugin = "<a href='/community_plugin/{}/{}.js' target='_blank' style='color: var(--primary-color) !important'>OPEN PLUGIN</a>".format(
                        repository.full_name, name
                    )
            else:
                open_plugin = ""

            # Hide/unhide
            if repository.installed or repository.custom:
                hide_option = ""
            else:
                if repository.hide:
                    hide_option = """
                        <li><a class="dropdown-list-item" href="{}/repository_unhide/{}" onclick="toggleLoading()">Unhide</a></li>
                    """.format(
                        self.url_path["api"], repository.repository_id
                    )
                else:
                    hide_option = """
                        <li><a class="dropdown-list-item" href="{}/repository_hide/{}" onclick="toggleLoading()">Hide</a></li>
                    """.format(
                        self.url_path["api"], repository.repository_id
                    )

            # Beta
            if repository.version_or_commit == "version":
                show_beta = '<li><a class="dropdown-list-item" href="{}/repository_{}_beta/{}" onclick="toggleLoading()">{}</a></li>'
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

            if (
                repository.homeassistant_version is not None
                and repository.version_or_commit == "version"
            ):
                if Version(HAVERSION[0:6]) < Version(
                    str(repository.homeassistant_version)
                ):
                    content += """
                        <div id="haversion" class="modal hacscolor">
                            <div class="modal-content">
                            <h5>Unsupported Home Assistant version</h5>
                            <p>{}</p>
                            </div>
                        </div>
                    """.format(
                        NOT_SUPPORTED_HA_VERSION.format(
                            HAVERSION,
                            repository.available_version,
                            repository.name,
                            str(repository.homeassistant_version),
                        )
                    )
                    main_action = main_action.replace(
                        "<a ", "<a class='modal-trigger' "
                    )
                    main_action = main_action.replace(
                        "{}/repository_install/{}".format(
                            self.url_path["api"], repository.repository_id
                        ),
                        "#haversion",
                    )

            if repository.installed:
                inst_ver = "<p><b>Installed {}:</b> {}</p>".format(
                    repository.version_or_commit,
                    repository.installed_version
                )
            else:
                inst_ver = ""

            last_ver = "<p><b>Available {}:</b> {}</p>".format(
                repository.version_or_commit,
                repository.available_version
            )

            if repository.status == "pending-update" and repository.version_or_commit == "version":
                changelog = "<a rel='noreferrer' href='https://github.com/{}/releases/{}' target='_blank' style='color: var(--primary-color) !important'>CHANGELOG</a>".format(
                    repository.repository_name, repository.available_version
                )
            else:
                changelog = ""

            if repository.installed and repository.repository_id != "172733314":
                uninstall = "<a href='{}/repository_uninstall/{}' style='float: right; color: var(--google-red-500) !important; font-weight: bold;' onclick='toggleLoading()'>UNINSTALL</a>".format(
                    self.url_path["api"], repository.repository_id
                )
            else:
                uninstall = ""

            ##################################################
            #          Version select
            if repository.published_tags and repository.repository_id != "172733314":
                options = ""
                for tag_name in repository.published_tags:
                    options += "<option class='hacscolor' value='{option}'>{option}</option>".format(option=tag_name)

                options += "<option class='hacscolor' value='{option}'>{option}</option>".format(option=repository.default_branch)
                if repository.selected_tag is not None:
                    selected = repository.selected_tag
                else:
                    selected = repository.available_version


                select_tag = """
                    <form action="{}/repository_select_tag/{}" name="selected_tag"
                            method="post" accept-charset="utf-8"
                            enctype="application/x-www-form-urlencoded"
                            class="hacs-form">
                        <select name="selected_tag" class="hacs-select" onchange="toggleLoading();document.getElementsByName('selected_tag')[0].submit()">
                            <option class="hacscolor" value="{}" selected hidden>{}</option>
                            {}
                        </select>
                    </form>
                """.format(
                    self.url_path["api"], repository.repository_id, selected, selected, options
                )
                last_ver = "<b>Available versions:</b> {}".format(select_tag)
            ##################################################



            #
            # CONTSTRUCT THE CARDS
            #

            main_content = self.load_element("repository/view_main")
            main_content = main_content.replace("{API}", self.url_path["api"])
            main_content = main_content.replace("{ID}", repository.repository_id)
            main_content = main_content.replace("{NAME}", repository.name)
            main_content = main_content.replace("{DESCRIPTION}", repository.description)
            main_content = main_content.replace("{REPOSITORY_NAME}", repository.repository_name)
            main_content = main_content.replace("{AUTHORS}", repository.display_authors)
            main_content = main_content.replace("{MAIN_ACTION}", main_action)
            main_content = main_content.replace("{UNINSTALL}", uninstall)
            main_content = main_content.replace("{CHANGELOG}", changelog)
            main_content = main_content.replace("{DROP-BETA}", show_beta)
            main_content = main_content.replace("{DROP-HIDE}", hide_option)
            main_content = main_content.replace("{INSTALLED}", inst_ver)
            main_content = main_content.replace("{AVAILABLE}", last_ver)
            main_content = main_content.replace("{OPEN_PLUGIN}", open_plugin)

            content += main_content

            info_container = self.load_element("repository/view_info")
            info_container = info_container.replace("{CONTENT}", repository.additional_info)
            info_container = info_container.replace("{NOTE}", note)
            content += info_container

            content += self.footer

        except IOError as exception:
        #except Exception as exception:
            _LOGGER.error(exception)
            raise web.HTTPFound(self.url_path["error"])

        return web.Response(body=content, content_type="text/html", charset="utf-8")
