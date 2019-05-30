"""Frontend header."""

async def header(hacs):
    """Generate a header element."""
    progressbar = await progress_bar(hacs)
    return f"""
      <div class="navbar-fixed">
        <nav class="nav-extended black">
          <div class="nav-content">
            <ul class="right tabs tabs-transparent">
              <li class="tab"><a href="{hacs.url_path["overview"]}">overview</a></li>
              <li class="tab"><a href="/community_store">store</a></li>
              <li class="tab"><a href="/community_settings">settings</a></li>
            </ul>
          </div>
        </nav>
      </div>
      {progressbar}
    """


async def progress_bar(hacs):
    """Generate a brogressbar."""
    if hacs.data["task_running"]:
        display = "block"
    else:
        display = "none"
    return """
    <div class="progress" id="progressbar" style="display: {}; background-color: #ffab405c">
        <div class="indeterminate" style="background-color: #ffab40"></div>
    </div>
    """.format(display)
