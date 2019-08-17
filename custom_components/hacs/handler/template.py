"""Custom template support."""
# pylint: disable=broad-except
from jinja2 import Template
from integrationhelper import Logger


def render_template(content, context):
    """Render templates in content."""
    # Fix None issues
    if context.releases.last_release_object is not None:
        prerelease = context.releases.last_release_object.prerelease
    else:
        prerelease = False

    # Render the template
    try:
        render = Template(content)
        render = render.render(
            installed=context.status.installed,
            pending_update=context.pending_upgrade,
            prerelease=prerelease,
            selected_tag=context.status.selected_tag,
            version_available=context.releases.last_release,
            version_installed=context.display_installed_version,
        )
        return render
    except Exception as exception:
        Logger("hacs.template").debug(exception)
        return content
