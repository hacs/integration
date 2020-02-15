"""Return repository information if any."""
from aiogithubapi import AIOGitHubException, AIOGitHub
from custom_components.hacs.handler.template import render_template
from custom_components.hacs.hacsbase.exceptions import HacsException


def info_file(repository):
    """get info filename."""
    if repository.repository_manifest.render_readme:
        for filename in ["readme", "readme.md", "README", "README.md", "README.MD"]:
            if filename in repository.treefiles:
                return filename
        return ""
    for filename in ["info", "info.md", "INFO", "INFO.md", "INFO.MD"]:
        if filename in repository.treefiles:
            return filename
    return ""


async def get_info_md_content(repository):
    """Get the content of info.md"""
    filename = info_file(repository)
    if not filename:
        return ""
    try:
        info = await repository.repository_object.get_contents(filename, repository.ref)
        if info is None:
            return ""
        info = info.content.replace("<svg", "<disabled").replace("</svg", "</disabled")
        return render_template(info, repository)
    except (AIOGitHubException, Exception):  # pylint: disable=broad-except
        return ""


async def get_repository(session, token, repository_full_name):
    """Return a repository object or None."""
    try:
        github = AIOGitHub(token, session)
        repository = await github.get_repo(repository_full_name)
        return repository
    except AIOGitHubException as exception:
        raise HacsException(exception)


async def get_tree(repository, ref):
    """Return the repository tree."""
    try:
        tree = await repository.get_tree(ref)
        return tree
    except AIOGitHubException as exception:
        raise HacsException(exception)
