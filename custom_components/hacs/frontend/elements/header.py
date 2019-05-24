"""Frontend header."""
from custom_components.hacs.const import DOMAIN_DATA


async def header(hass):
    """Generate a header element."""
    progressbar = await progress_bar(hass)
    return """
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
      {}
    """.format(
        progressbar
    )


async def progress_bar(hass):
    """Generate a brogressbar."""
    if data["commander"].task_running:
        display = "block"
    else:
        display = "none"
    return """
    <div class="progress" id="progressbar" style="display: {}; background-color: #ffab405c">
        <div class="indeterminate" style="background-color: #ffab40"></div>
    </div>
    """.format(display)
