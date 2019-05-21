"""Generate UI elements for a element."""
import logging

from custom_components.hacs.frontend.elements import warning_card

_LOGGER = logging.getLogger(__name__)


class Generate:
    """Generator for UI elements."""

    def __init__(self, hass, element):
        """Initialize."""
        self.hass = hass
        self.element = element

    async def authors(self):
        """Generate authors."""
        _LOGGER.debug("Generating authors for %s", self.element.element_id)

        if not self.element.authors:
            return ""

        authors = "<p>Author(s): "
        for author in self.element.authors:

            if "@" in author:
                author = author.split("@")[-1]

            authors += """
              <a href="https://github.com/{author}"
                target="_blank"
                style="margin: 2">
                @{author}
              </a>
            """.format(
                author=author
            )

        authors += "</p>"
        return authors

    async def avaiable_version(self):
        """Generate avaiable version."""
        _LOGGER.debug("Generating avaiable version for %s", self.element.element_id)

        return """
          <p>
            <b>Available version:</b> {}
          </p>
          </br>
        """.format(
            self.element.avaiable_version
        )

    async def card_icon(self):
        """Generate avaiable version."""
        _LOGGER.debug("Generating card icon for %s", self.element.element_id)

        card_icon = ""

        if self.element.restart_pending:
            card_icon = """
              <i class='fas fa-info'
                style='font-size: 18px; float: right; color: #a70000'>
              </i>
            """
        elif self.element.isinstalled:
            if self.element.installed_version != self.element.avaiable_version:
                card_icon = """
                  <i class='fas fa-arrow-up'
                    style='font-size: 18px; float: right; color: #ffab40'>
                  </i>
                """
        return card_icon

    async def changelog(self):
        """Generate changelog link."""
        _LOGGER.debug("Generating changelog link for %s", self.element.element_id)

        if not self.element.isinstalled:
            return ""

        if self.element.installed_version == self.element.avaiable_version:
            return ""

        return """
          <a href="https://github.com/{}/releases" target="_blank">
            CHANGELOG
          </a>
        """.format(
            self.element.repo
        )

    async def description(self):
        """Generate description version."""
        _LOGGER.debug("Generating description for %s", self.element.element_id)

        return """
          <p>
            {}
          </p>
          </br>
        """.format(
            self.element.description
        )

    async def element_note(self):
        """Generate element note."""
        _LOGGER.debug("Generating element note for %s", self.element.element_id)

        if self.element.element_type == "integration":
            return """
              </br>
              <i>
                When installed, this will be located in '{}/custom_components/{}/',
                you still need to add it to your 'configuration.yaml' file.
              </i>
              </br></br>
              <i>
                To learn more about how to configure this,
                click the "REPO" button to get to the repoistory for this integration.
              </i>
            """.format(
                self.hass.config.path(), self.element.element_id
            )

        elif self.element.element_type == "plugin":
            if "lovelace-" in self.element.element_id:
                file_name = self.element.element_id.split("lovelace-")[-1]
            else:
                file_name = self.element.element_id

            return """
              </br>
              <i>
                When installed, this will be located in '{config}/www/community/{element}',
                you still need to add it to your lovelace configuration ('ui-lovelace.yaml' or the raw UI config editor).
              </i>
              </br></br>
              <i>
                When you add this to your configuration use this as the URL:
              </i>
              </br>
              <pre class="yaml">url: /community_plugin/{element}/{file_name}.js</pre>
              </br></br>
              <i>
                To learn more about how to configure this,
                click the "REPO" button to get to the repoistory for this plugin.
              </i>
            """.format(
                config=self.hass.config.path(),
                element=self.element.element_id,
                file_name=file_name,
            )
        else:
            return ""

    async def info(self):
        """Generate info."""
        import markdown

        _LOGGER.debug("Generating info for %s", self.element.element_id)

        if self.element.info is None:
            return ""

        markdown_render = markdown.markdown(
            self.element.info,
            extensions=["markdown.extensions.tables", "markdown.extensions.codehilite"],
        )
        markdown_render = markdown_render.replace("<h3>", "<h6>").replace(
            "</h3>", "</h6>"
        )
        markdown_render = markdown_render.replace("<h2>", "<h5>").replace(
            "</h2>", "</h5>"
        )
        markdown_render = markdown_render.replace("<h1>", "<h4>").replace(
            "</h1>", "</h4>"
        )
        markdown_render = markdown_render.replace("<code>", "<pre>").replace(
            "</code>", "</pre>"
        )
        markdown_render = markdown_render.replace(
            "<table>", "<table class='responsive-table white-text'>"
        )
        return "<span>{}</span>".format(markdown_render)

    async def installed_version(self):
        """Generate installed version."""
        _LOGGER.debug("Generating installed version for %s", self.element.element_id)

        if self.element.installed_version is None:
            return ""

        return """
          <p>
            <b>Installed version:</b> {}
          </p>
        """.format(
            self.element.installed_version
        )

    async def main_action(self):
        """Generate main action."""
        _LOGGER.debug("Generating main action for %s", self.element.element_id)

        if not self.element.isinstalled:
            action = "install"
            title = action

        else:
            if self.element.installed_version == self.element.avaiable_version:
                action = "install"
                title = "reinstall"
            else:
                action = "upgrade"
                title = action

        return """
          <a href="/community_api/{}/{}"
            onclick="document.getElementById('progressbar').style.display = 'block'">
            {}
          </a>
        """.format(
            self.element.element_id, action, title
        )

    async def repo(self):
        """Generate repo link."""
        _LOGGER.debug("Generating repo link for %s", self.element.element_id)

        return """
          <a href="https://github.com/{}" target="_blank">
            REPO
          </a>
        """.format(
            self.element.repo
        )

    async def restart_pending(self):
        """Generate main action."""
        _LOGGER.debug("Generating main action for %s", self.element.element_id)

        if not self.element.restart_pending or self.element.element_type == "plugin":
            return ""

        title = "Restart pending"
        message = (
            "You need to restart Home Assisant, for your last operation to be loaded."
        )

        return await warning_card(message, title)

    async def uninstall(self):
        """Generate main action."""
        _LOGGER.debug("Generating main action for %s", self.element.element_id)

        if not self.element.isinstalled:
            return ""

        return """
          <a href="/community_api/{}/uninstall"
            style="float: right; color: #a70000; font-weight: bold;"
            onclick="document.getElementById('progressbar').style.display = 'block'">
            UNINSTALL
          </a>
        """.format(
            self.element.element_id
        )
