"""Custom template support."""
# pylint: disable=broad-except
from jinja2 import Template

from custom_components.hacs.helpers.functions.logger import getLogger

logger = getLogger("template")


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
            installed=context.data.installed,
            pending_update=context.pending_upgrade,
            prerelease=prerelease,
            selected_tag=context.data.selected_tag,
            version_available=context.releases.last_release,
            version_installed=context.display_installed_version,
        )
        return render
    except (Exception, BaseException) as exception:
        logger.debug(exception)
        return content
