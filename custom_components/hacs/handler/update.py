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

    repo, last_release, ref = None, None, None
    git = hass.data[DOMAIN_DATA]["commander"].git

    if repo_name in hass.data[DOMAIN_DATA]["commander"].skip:
        _LOGGER.debug("%s in 'skip', skipping", repo_name)
        return repo, last_release, ref

    _LOGGER.debug("Loading from data from GitHub for %s", repo_name)

    try:
        repo = git.get_repo(repo_name)
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.debug(error)
        _LOGGER.debug("Skipping %s on next run.", repo_name)
        hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)

    # Find GitHub releases.
    try:
        last_release = list(repo.get_releases())[0].tag_name
        ref = "tags/{}".format(last_release)
    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.debug(error)

    return repo, last_release, ref


async def load_integrations_from_git(hass, repo_name):
    """
    Load integration data from GitHub repo.

    For integraions to be accepted, three criterias must be met in the GitHub repo.
        - There are GitHub releases
        - The integration is located under RepoRoot/custom_components/integration_name
        - There is a manifest.json file under RepoRoot/custom_components/integration_name/

    This function checks those requirements
    If any of them fails, the repo will be added to a 'skip' list.
    """
    repo, last_release, ref = await prosess_repo_request(hass, repo_name)

    if repo is None or last_release is None or ref is None:
        hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
        _LOGGER.debug("Could not prosess %s", repo_name)
        _LOGGER.debug("Skipping %s on next run.", repo_name)
        return

    # Find component location
    try:
        integration_dir = repo.get_dir_contents("custom_components", ref)[0].path
        integration_dir_contents = repo.get_dir_contents(integration_dir, ref)

        manifest_path = "{}/manifest.json".format(integration_dir)

        content = []
        for item in list(integration_dir_contents):
            content.append(item.path)

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
        _LOGGER.debug(error)  # TODO: Remove all unnecessary log statements, for things that we expect to fail.

    # PrettyDescription
    element.description = "" if element.description is None else element.description

    # Save it back to hass.data
    hass.data[DOMAIN_DATA]["elements"][element.element_id] = element


async def load_plugins_from_git(hass, repo_name):
    """
    Load plugin data from GitHub repo.

    For integraions to be accepted, three criterias must be met in the GitHub repo.
        - There are GitHub releases
        - The plugin is located under RepoRoot/dist/ or RepoRoot/
        - One of the js files needs to match the repo name. # TODO: This should fail the scan

    This function checks those requirements
    If any of them fails, the repo will be added to a 'skip' list.
    """
    repo, last_release, ref = await prosess_repo_request(hass, repo_name)

    if repo is None or last_release is None or ref is None:
        hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
        _LOGGER.debug("Could not prosess %s", repo_name)
        _LOGGER.debug("Skipping %s on next run.", repo_name)
        return

    plugin_name = repo_name.split("/")[-1]

    # Load existing Element object.
    if plugin_name in hass.data[DOMAIN_DATA]["elements"]:
        element = hass.data[DOMAIN_DATA]["elements"][plugin_name]
    else:
        element = Element("plugin", plugin_name)

    # Try to find files
    files = []

    repo_root = repo.get_dir_contents("", ref)

    if element.remote_dir_location is None:
        # Try RepoRoot/dist/
        try:
            test_remote_dir_location = repo.get_dir_contents("dist", ref)
            for file in list(test_remote_dir_location):
                if file.name.endswith(".js"):
                    files.append(file)
                if files:
                    element.remote_dir_location = "dist"
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug(error)

    if element.remote_dir_location is None:
        # Try RepoRoot/
        try:
            for file in list(repo_root):
                if file.name.endswith(".js"):
                    files.append(file)
                    if files:
                        element.remote_dir_location = "root"
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug(error)

    if element.remote_dir_location is None:
        _LOGGER.debug("Can't find any acceptable files in %s", repo_name)
        _LOGGER.debug(files)
        _LOGGER.debug("Skipping %s on next run.", repo_name)
        hass.data[DOMAIN_DATA]["commander"].skip.append(repo_name)
        return

    ################### Load basic info from repo. ###################

    element.name = plugin_name
    element.avaiable_version = last_release
    element.description = repo.description
    element.repo = repo_name

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
