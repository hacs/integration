"""Custom template support."""
from jinja2 import Template

def render_template(content, context):
    """Render templates in content."""
    # Fix None issues
    if context.last_release_object is not None:
        prerelease = context.last_release_object.prerelease
    else:
        prerelease = False




    # Render the template
    try:
        render = Template(content)
        render = render.render(
            installed=context.installed,
            pending_update=context.pending_update,
            prerelease=prerelease,
            selected_tag=context.selected_tag,
            version_available=context.last_release_tag,
            version_installed=context.version_installed
        )
        return render
    except Exception as exception:
        context.logger.warning("Error rendering info template {}".format(exception), "template")
        return content
