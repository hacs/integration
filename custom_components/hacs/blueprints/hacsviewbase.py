"""Blueprint for HacsViewBase."""
import logging
from homeassistant.components.http import HomeAssistantView

_LOGGER = logging.getLogger(__name__)


class HacsViewBase(HomeAssistantView):
    """Base View Class for HACS."""
    requires_auth = False

    def __init__(self, hacs):
        """Initialize view."""
        self.hacs = hacs
        self.styles = self.load_styles()

    def load_styles(self):
        """Load styles from CSS file."""
        style = ""
        file = f"{self.hacs.config_dir}/custom_components/hacs/frontend/elements/hacs.css"
        with open(file) as cssfile:
            style = cssfile.read()
            cssfile.close()
        return f"<style>{style}</style>"

    @property
    def base_content(self):
        """Base content."""
        return f"""
          {self.load_imports}
          {self.load_styles}
          {self.load_scripts}
          {self.load_header}
          {self.load_progress_bar}
        """

    @property
    def imports(self):
        """Load imports."""
        return """
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/css/materialize.min.css">
        <link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.8.2/css/all.css" integrity="sha384-oS3vJWv+0UjzBfQzYUhtDYW+Pj2yciDJxpsK1OYPAYjqT085Qq/1cq5FLXAZQ7Ay" crossorigin="anonymous">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/materialize/1.0.0/js/materialize.min.js"></script>
        """

    @property
    def scripts(self):
        """Load scripts."""
        return ""

    @property
    def header(self):
        """Load header."""
        return f"""
        <div class="navbar-fixed">
          <nav class="nav-extended black">
            <div class="nav-content">
              <ul class="right tabs tabs-transparent">
                <li class="tab"><a href="/community_overview">overview</a></li>
                <li class="tab"><a href="/community_store">store</a></li>
                <li class="tab"><a href="/community_settings">settings</a></li>
              </ul>
            </div>
          </nav>
        </div>
        """

    @property
    def progress_bar(self):
        """Load progress bar."""
        if self.hacs.task_running:
            display = "block"
        else:
            display = "none"

        return f"""
        <div class="progress" id="progressbar" style="display: {display}; background-color: #ffab405c">
            <div class="indeterminate" style="background-color: #ffab40"></div>
        </div>
        """
