"""Return repository information if any."""
import json

from aiogithubapi import AIOGitHubAPIException

from ..exceptions import HacsException


async def get_tree(repository, ref):
    """Return the repository tree."""
    try:
        tree = await repository.get_tree(ref)
        return tree
    except (ValueError, AIOGitHubAPIException) as exception:
        raise HacsException(exception)


async def get_releases(repository, prerelease=False, returnlimit=5):
    """Return the repository releases."""
    try:
        releases = await repository.get_releases(prerelease, returnlimit)
        return releases
    except (ValueError, AIOGitHubAPIException) as exception:
        raise HacsException(exception)


async def get_integration_manifest(repository):
    """Return the integration manifest."""
    if repository.data.content_in_root:
        manifest_path = "manifest.json"
    else:
        manifest_path = f"{repository.content.path.remote}/manifest.json"
    if not manifest_path in [x.full_path for x in repository.tree]:
        raise HacsException(f"No file found '{manifest_path}'")
    try:
        manifest = await repository.repository_object.get_contents(manifest_path, repository.ref)
        manifest = json.loads(manifest.content)
    except BaseException as exception:  # pylint: disable=broad-except
        raise HacsException(f"Could not read manifest.json [{exception}]")

    try:
        repository.integration_manifest = manifest
        repository.data.authors = manifest["codeowners"]
        repository.data.domain = manifest["domain"]
        repository.data.manifest_name = manifest["name"]
        repository.data.config_flow = manifest.get("config_flow", False)

        # Set local path
        repository.content.path.local = repository.localpath

    except KeyError as exception:
        raise HacsException(f"Missing expected key {exception} in '{manifest_path}'") from exception
