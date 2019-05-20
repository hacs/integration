"""Return a generic button."""


async def generic_button_local(target, text):
    """Return a button, and activate the progressbar."""
    return """
    <a href='{}'
        class='waves-effect waves-light btn'
        onclick="document.getElementById('progressbar').style.display = 'block'">
        {}
    </a>
    """.format(
        target, text
    )


async def generic_button_external(target, text):
    """Return a button."""
    return """
        <a href='{}'
            class='waves-effect waves-light btn'
            target="_blank" style="float: right; margin-left: 3%">
            {}
        </a>
    """.format(
        target, text
    )
