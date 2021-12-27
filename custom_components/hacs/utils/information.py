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


def find_file_name(repository):
    """Get the filename to target."""
    if repository.data.category == "plugin":
        get_file_name_plugin(repository)
    elif repository.data.category == "integration":
        get_file_name_integration(repository)
    elif repository.data.category == "theme":
        get_file_name_theme(repository)
    elif repository.data.category == "appdaemon":
        get_file_name_appdaemon(repository)
    elif repository.data.category == "python_script":
        get_file_name_python_script(repository)

    if repository.hacs.system.action:
        repository.logger.info(f"filename {repository.data.file_name}")
        repository.logger.info(f"location {repository.content.path.remote}")


def get_file_name_plugin(repository):
    """Get the filename to target."""
    tree = repository.tree
    releases = repository.releases.objects

    if repository.data.content_in_root:
        possible_locations = [""]
    else:
        possible_locations = ["release", "dist", ""]

    # Handler for plug requirement 3
    if repository.data.filename:
        valid_filenames = [repository.data.filename]
    else:
        valid_filenames = [
            f"{repository.data.name.replace('lovelace-', '')}.js",
            f"{repository.data.name}.js",
            f"{repository.data.name}.umd.js",
            f"{repository.data.name}-bundle.js",
        ]

    for location in possible_locations:
        if location == "release":
            if not releases:
                continue
            release = releases[0]
            if not release.assets:
                continue
            asset = release.assets[0]
            for filename in valid_filenames:
                if filename == asset.name:
                    repository.data.file_name = filename
                    repository.content.path.remote = "release"
                    break

        else:
            for filename in valid_filenames:
                if f"{location+'/' if location else ''}{filename}" in [x.full_path for x in tree]:
                    repository.data.file_name = filename.split("/")[-1]
                    repository.content.path.remote = location
                    break


def get_file_name_integration(repository):
    """Get the filename to target."""


def get_file_name_theme(repository):
    """Get the filename to target."""
    tree = repository.tree

    for treefile in tree:
        if treefile.full_path.startswith(
            repository.content.path.remote
        ) and treefile.full_path.endswith(".yaml"):
            repository.data.file_name = treefile.filename


def get_file_name_appdaemon(repository):
    """Get the filename to target."""


def get_file_name_python_script(repository):
    """Get the filename to target."""
    tree = repository.tree

    for treefile in tree:
        if treefile.full_path.startswith(
            repository.content.path.remote
        ) and treefile.full_path.endswith(".py"):
            repository.data.file_name = treefile.filename
