"""Frontend header."""


async def header():
    """Generate a header element."""
    progressbar = await progress_bar()
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


async def progress_bar():
    """Generate a brogressbar."""
    return """
    <div class="progress" id="progressbar" style="display: none">
        <div class="indeterminate"></div>
    </div>
    """
