"""Return repository information if any."""
import json
from aiogithubapi import AIOGitHubException, AIOGitHub
from custom_components.hacs.handler.template import render_template
from custom_components.hacs.hacsbase.exceptions import HacsException


def info_file(repository):
    """get info filename."""
    if repository.data.render_readme:
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


async def get_releases(repository, prerelease=False, returnlimit=5):
    """Return the repository releases."""
    try:
        releases = await repository.get_releases(prerelease, returnlimit)
        return releases
    except AIOGitHubException as exception:
        raise HacsException(exception)


async def get_integration_manifest(repository):
    """Return the integration manifest."""
    manifest_path = f"{repository.content.path.remote}/manifest.json"
    if not manifest_path in [x.full_path for x in repository.tree]:
        raise HacsException(f"No file found '{manifest_path}'")
    try:
        manifest = await repository.repository_object.get_contents(
            manifest_path, repository.ref
        )
        manifest = json.loads(manifest.content)
    except Exception as exception:  # pylint: disable=broad-except
        raise HacsException(f"Could not read manifest.json [{exception}]")

    try:
        repository.manifest = manifest
        repository.information.authors = manifest["codeowners"]
        repository.domain = manifest["domain"]
        repository.information.name = manifest["name"]
        repository.information.homeassistant_version = manifest.get("homeassistant")

        # Set local path
        repository.content.path.local = repository.localpath

    except KeyError as exception:
        raise HacsException(f"Missing expected key {exception} in 'manifest.json'")
