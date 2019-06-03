"""Blueprint for HacsViewBase."""
from homeassistant.components.http import HomeAssistantView
from .hacsbase import HacsBase


class HacsViewBase(HomeAssistantView, HacsBase):
    """Base View Class for HACS."""
    requires_auth = False

    @property
    def base_content(self):
        """Base content."""
        return """
            <head>
                {}
            </head>
            {}
            {}
        """.format(self.imports, self.header, self.progress_bar)

    @property
    def imports(self):
        """Load imports."""
        return """
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
        <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.8.2/css/all.css" integrity="sha384-oS3vJWv+0UjzBfQzYUhtDYW+Pj2yciDJxpsK1OYPAYjqT085Qq/1cq5FLXAZQ7Ay" crossorigin="anonymous">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"/></script>
        <link rel="stylesheet" href="{}/hacs.css">
        <script src="{}/hacs.js"></script>
        """.format(self.url_path["static"], self.url_path["static"])

    @property
    def header(self):
        """Load header."""
        return """
        <div class="navbar-fixed">
          <nav class="nav-extended black">
            <div class="nav-content">
              <ul class="right tabs tabs-transparent">
                <li class="tab"><a href="{}">overview</a></li>
                <li class="tab"><a href="{}">store</a></li>
                <li class="tab right"><a href="{}">settings</a></li>
              </ul>
            </div>
          </nav>
        </div>
        """.format(self.url_path["overview"], self.url_path["store"], self.url_path["settings"])

    @property
    def progress_bar(self):
        """Load progress bar."""
        if self.data["task_running"]:
            display = "block"
        else:
            display = "none"

        return """
        <div style="display: {}"><p>Background task running, refresh the page in a little while.</p></div>
        <div class="progress" id="progressbar" style="display: {}; background-color: #ffab405c">
            <div class="indeterminate" style="background-color: #ffab40"></div>
        </div>
        """.format(display, display)
