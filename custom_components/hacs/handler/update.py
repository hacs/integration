"""Update data."""
import logging
import json
from custom_components.hacs.element import Element
from custom_components.hacs.const import DOMAIN_DATA
from custom_components.hacs.handler.storage import write_to_data_store

_LOGGER = logging.getLogger(__name__)


async def update_data_after_action(hass, element):
    """
    Updates the data we have of the element after an action is completed.
    """

    # Update the data
    hass.data[DOMAIN_DATA]["elements"][element.element_id] = element

    # Save the data to storage.
    await write_to_data_store(hass.config.path(), hass.data[DOMAIN_DATA])


async def prosess_repo_request(hass, repo_name):
    """Initial prosessing of the repo."""
    _LOGGER.debug("Started prosessing %s", repo_name)

    repo, last_release, last_update, ref, releases = None, None, None, None, []

    git = hass.data[DOMAIN_DATA]["commander"].git

    if repo_name in hass.data[DOMAIN_DATA]["commander"].skip:
        _LOGGER.debug("%s in 'skip', skipping", repo_name)
        return repo, last_release, last_update, ref, releases

    _LOGGER.debug("Loading from data from GitHub for %s", repo_name)

    try:
        repo = git.get_repo(repo_name)
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Could not find repo for %s - %s", repo_name, error)
        _LOGGER.debug("Skipping %s on next run.", repo_name)
        hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
        return repo, last_release, last_update, ref, releases

    # Find GitHub releases.
    try:
        github_releases = list(repo.get_releases())
        if github_releases:
            release = github_releases[0]
            last_release = release.tag_name
            last_update = release.created_at.strftime("%d %b %Y %H:%M:%S")
            ref = "tags/{}".format(last_release)

            for release in github_releases:
                releases.append(release.tag_name)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.debug("No releases found for %s - %s", repo_name, str(releases))

    if not releases:
        try:
            ref = repo.default_branch
            last_update = repo.updated_at.strftime("%d %b %Y %H:%M:%S")

        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error("There was an issue parsing data for %s", repo_name)

    return repo, last_release, last_update, ref, releases


async def load_integrations_from_git(hass, repo_name):
    """
    Load integration data from GitHub repo.
    """
    repo, last_release, last_update, ref, releases = await prosess_repo_request(
        hass, repo_name
    )

    if repo is None or ref is None:
        if repo_name not in hass.data[DOMAIN_DATA]["commander"].skip:
            hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
        _LOGGER.debug("Could not prosess %s", repo_name)
        _LOGGER.debug("Skipping %s on next run.", repo_name)
        return

    _LOGGER.debug(
        "%s info:  ref: '%s'  last_update: '%s'  releases: '%s'  last_release: '%s'",
        repo.name,
        ref,
        last_update,
        str(releases),
        last_release,
    )

    # Find component location
    try:
        integration_dir = repo.get_dir_contents("custom_components", ref)[0].path
        integration_dir_contents = repo.get_dir_contents(integration_dir, ref)

        manifest_path = "{}/manifest.json".format(integration_dir)

        content = []
        for item in list(integration_dir_contents):
            content.append(item.path)

        _LOGGER.debug("Integration content %s", str(content))

        if not content:
            hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
            _LOGGER.debug("Can't get data from %s (no content)", repo_name)
            _LOGGER.debug("Skipping %s on next run.", repo_name)
            return

        if manifest_path not in content:
            hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
            _LOGGER.debug("Can't get data from %s (missing manifest)", repo_name)
            _LOGGER.debug("Skipping %s on next run.", repo_name)
            return

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.debug(error)

    # Load manifest
    try:
        manifest = repo.get_file_contents(manifest_path, ref)
        manifest = json.loads(manifest.decoded_content.decode())
    except Exception as error:  # pylint: disable=broad-except
        hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
        _LOGGER.debug("Can't load manifest from %s", repo_name)
        _LOGGER.debug("Skipping %s on next run.", repo_name)
        return

    # Check if manifest is valid
    if len(manifest["domain"].split()) > 1 or "http" in manifest["domain"]:
        hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
        _LOGGER.debug("Manifest is not valid for %s", repo_name)
        _LOGGER.debug("Skipping %s on next run.", repo_name)
        return

    ###################################################################
    ################### We can now trust this repo. ###################
    ###################################################################

    # Load existing Element object from hass.data if it exists.
    if manifest["domain"] in hass.data[DOMAIN_DATA]["elements"]:
        element = hass.data[DOMAIN_DATA]["elements"][manifest["domain"]]
    else:
        # Create new Element object.
        element = Element("integration", manifest["domain"])

    ################### Load basic info from repo. ###################

    element.avaiable_version = last_release
    element.description = repo.description
    element.repo = repo_name
    element.releases = releases
    element.last_update = last_update

    ################# Load basic info from manifest. #################

    element.authors = manifest["codeowners"]
    element.name = manifest["name"]
    element.element_id = manifest["domain"]

    ################### Load custom info from repo. ###################

    # Get info.md
    try:
        info = repo.get_file_contents("info.md", ref).decoded_content.decode()
        element.info = info
    except Exception as error:  # pylint: disable=broad-except
        element.info = ""
        _LOGGER.debug(
            error
        )  # TODO: Remove all unnecessary log statements, for things that we expect to fail.

    # PrettyDescription
    element.description = "" if element.description is None else element.description

    # Save it back to hass.data
    hass.data[DOMAIN_DATA]["elements"][element.element_id] = element

    return True


async def load_plugins_from_git(hass, repo_name):
    """
    Load plugin data from GitHub repo.
    """
    repo, last_release, last_update, ref, releases = await prosess_repo_request(
        hass, repo_name
    )

    if repo is None or ref is None:
        if repo_name not in hass.data[DOMAIN_DATA]["commander"].skip:
            hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
        _LOGGER.debug("Could not prosess %s", repo_name)
        _LOGGER.debug("Skipping %s on next run.", repo_name)
        return

    _LOGGER.debug(
        "%s info:  ref: '%s'  last_update: '%s'  releases: '%s'  last_release: '%s'",
        repo.name,
        ref,
        last_update,
        str(releases),
        last_release,
    )

    plugin_name = repo_name.split("/")[-1]

    # Load existing Element object.
    if plugin_name in hass.data[DOMAIN_DATA]["elements"]:
        element = hass.data[DOMAIN_DATA]["elements"][plugin_name]
    else:
        element = Element("plugin", plugin_name)

    # Try to find files
    files = []

    repo_root = repo.get_dir_contents("", ref)

    if element.remote_dir_location is None or element.remote_dir_location == "root":
        # Try RepoRoot/
        try:
            for file in list(repo_root):
                if file.name.endswith(".js"):
                    files.append(file.name)
            if files:
                element.remote_dir_location = "root"
            else:
                _LOGGER.debug("Could not find any files in /")
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug("Could not find any files in / - %s", error)

    if element.remote_dir_location is None or element.remote_dir_location == "dist":
        # Try RepoRoot/dist/
        try:
            test_remote_dir_location = repo.get_dir_contents("dist", ref)
            for file in list(test_remote_dir_location):
                if file.name.endswith(".js"):
                    files.append(file.name)
            if files:
                element.remote_dir_location = "dist"
            else:
                _LOGGER.debug("Could not find any files in dist/")
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug("Could not find any files in dist/ - %s", error)

    _LOGGER.debug("plugin content %s", str(files))

    # Handler for requirement 3
    find_file = "{}.js".format(repo_name.split("/")[1].replace("lovelace-", ""))
    if find_file not in files:
        element.remote_dir_location = None

        if repo_name not in hass.data[DOMAIN_DATA]["commander"].skip:
            hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
        _LOGGER.debug(
            "Expected file %s not found in %s for %s", find_file, files, repo_name
        )
        _LOGGER.debug("Skipping %s on next run.", repo_name)
        return

    ################### Load basic info from repo. ###################

    element.name = plugin_name
    element.avaiable_version = last_release
    element.description = repo.description
    element.repo = repo_name
    element.releases = releases
    element.last_update = last_update

    ################### Load custom info from repo. ###################

    # Get info.md
    try:
        info = repo.get_file_contents("info.md", ref).decoded_content.decode()
        element.info = info
    except Exception as error:  # pylint: disable=broad-except
        element.info = ""
        _LOGGER.debug(error)

    # PrettyDescription
    element.description = "" if element.description is None else element.description

    # Save it back to hass.data
    hass.data[DOMAIN_DATA]["elements"][plugin_name] = element

    return True
