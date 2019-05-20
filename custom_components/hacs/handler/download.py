"""Download."""
import logging
import os

import async_timeout

from custom_components.hacs.const import DOMAIN_DATA
from custom_components.hacs.handler.remove import remove_element
from custom_components.hacs.handler.storage import write_to_data_store
from custom_components.hacs.handler.update import update_data_after_action
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


async def async_download_file(hass, url):
    """
    Download files, and return the content.
    """
    _LOGGER.debug("Donwloading from %s", url)

    # There is a bug somewhere... TODO: Find that bug....
    if "tags/" in url:
        _LOGGER.debug(
            "tags/ are in '%s', this is beeing removed, but this IS a bug.", url
        )
        url = url.replace("tags/", "")

    result = None

    with async_timeout.timeout(5, loop=hass.loop):
        request = await async_get_clientsession(hass).get(url)

        # Make sure that we got a valid result
        if request.status == 200:
            result = await request.text()
        else:
            _LOGGER.error(
                "Got status code %s when trying to download %s", request.status, url
            )
    return result


async def download_integration(hass, integration):
    """
    Download an integration.
    This will create the required directory, and download any files needed for the integration to function.
    """
    git = hass.data[DOMAIN_DATA]["commander"].git

    integrationdir = "{}/custom_components/{}".format(
        hass.config.path(), integration.element_id
    )

    # Recreate the integration directory.
    try:
        if os.path.exists(integrationdir):
            _LOGGER.debug(
                "%s exist, deleting current content before download.", integrationdir
            )
            await remove_element(hass, integration)

        # Create the new directory
        os.mkdir(integrationdir)

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Creating directory %s failed with %s", integrationdir, error)
        return

    # Okey, the directory structure is now OK, let's continue.
    try:
        repo = git.get_repo(integration.repo)

        # Make sure that we use the correct version (ref).
        ref = "tags/{}".format(integration.avaiable_version)

        # Get the first dir in the "custom_components" directory.
        remote_dir_name = repo.get_dir_contents("custom_components", ref)[0].path

        # Get the contents of the remote integration.
        remote_integration_dir = repo.get_dir_contents(remote_dir_name, ref)

        _LOGGER.debug("Content in remote repo %s", str(list(remote_integration_dir)))

        # Download all the files.
        for file in remote_integration_dir:
            _LOGGER.debug("Downloading %s", file.path)

            filecontent = await async_download_file(hass, file.download_url)

            if filecontent is None:
                _LOGGER.error("There was an error downloading the file %s", file.path)
                continue

            # Save the content of the file.
            local_file_path = "{}/{}".format(integrationdir, file.name)
            with open(
                local_file_path, "w", encoding="utf-8", errors="ignore"
            ) as outfile:
                outfile.write(filecontent)
                outfile.close()

        # Update hass.data
        integration.installed_version = integration.avaiable_version
        integration.isinstalled = True
        integration.restart_pending = True
        await update_data_after_action(hass, integration)

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error(
            "This sucks! There was an issue downloading the integration - %s", error
        )


async def download_plugin(hass, plugin):
    """
    Download a plugin.

    This will create the required directory, and download any files needed for the plugin to function.
    """
    git = hass.data[DOMAIN_DATA]["commander"].git

    www_dir = "{}/www".format(hass.config.path())
    plugin_base_dir = "{}/community".format(www_dir)
    plugin_dir = "{}/{}".format(plugin_base_dir, plugin.element_id)

    # Create the www directory.
    try:
        if not os.path.exists(www_dir):
            os.mkdir(www_dir)

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Creating directory %s failed with %s", www_dir, error)
        return

    # Create the base plugin directory.
    try:
        if not os.path.exists(plugin_base_dir):
            os.mkdir(plugin_base_dir)

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Creating directory %s failed with %s", plugin_base_dir, error)
        return

    # Create the plugin directory.
    try:
        if os.path.exists(plugin_dir):
            _LOGGER.debug(
                "%s exist, deleting current content before download.", plugin_dir
            )
            await remove_element(hass, plugin)

        # Create the new directory
        os.mkdir(plugin_dir)

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("Creating directory %s failed with %s", plugin_dir, error)
        return

    # Okey, the directory structure is now OK, let's continue.
    try:
        repo = git.get_repo(plugin.repo)
        ref = "tags/{}".format(plugin.avaiable_version)

        # Plugins have two supported locations, wee need to check both...
        remotedir = None

        if plugin.remote_dir_location is not None:
            if plugin.remote_dir_location == "root":
                remotedir = repo.get_dir_contents("", ref)
            elif plugin.remote_dir_location == "dist":
                remotedir = repo.get_dir_contents("dist", ref)
            else:
                _LOGGER.debug("%s is not valid", plugin.remote_dir_location)

        # Try ROOT/dist/
        if remotedir is None:
            try:
                remotedir = repo.get_dir_contents("dist", ref)
            except Exception as error:  # pylint: disable=broad-except
                _LOGGER.debug("No content found in ROOT/dist.")

        # Try ROOT/
        if remotedir is None:
            try:
                remotedir = repo.get_dir_contents("", ref)
            except Exception as error:  # pylint: disable=broad-except
                _LOGGER.error(
                    "This sucks! We could not locate ANY files to download - %s", error
                )
                return

        _LOGGER.debug("Content in remote repo %s", str(list(remotedir)))

        for file in remotedir:

            # We will only handle .js files
            if not file.name.endswith(".js"):
                continue

            _LOGGER.debug("Downloading %s", file.path)

            filecontent = await async_download_file(hass, file.download_url)

            if filecontent is None:
                _LOGGER.error("There was an error downloading the file %s", file.path)
                continue

            # Save the content of the file.
            local_file_path = "{}/{}".format(plugin_dir, file.name)
            with open(
                local_file_path, "w", encoding="utf-8", errors="ignore"
            ) as outfile:
                outfile.write(filecontent)
                outfile.close()

        # Update hass.data
        plugin.installed_version = plugin.avaiable_version
        plugin.isinstalled = True
        plugin.restart_pending = False
        await update_data_after_action(hass, plugin)

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error(
            "This sucks! There was an issue downloading the plugin - %s", error
        )


async def download_hacs(hass):
    """
    Special function to update HACS.
    """
    git = hass.data[DOMAIN_DATA]["commander"].git
    hacs_directory = "{}/custom_components/hacs".format(hass.config.path())

    try:
        repo = git.get_repo("custom-components/hacs")
        ref = "tags/{}".format(hass.data[DOMAIN_DATA]["hacs"]["remote"])

        remote_dir = repo.get_dir_contents("custom_components/hacs", ref)

        _LOGGER.debug("Content in remote repo %s", str(list(remote_dir)))

        # Download the content of "hacs"
        try:
            for file in remote_dir:
                # We download sub dirs at a later stage.
                if file.type == "dir":
                    _LOGGER.debug("%s is a directory, skipping.", file.name)

                _LOGGER.debug("Downloading %s", file.path)

                filecontent = await async_download_file(hass, file.download_url)
                if filecontent is None:
                    _LOGGER.error(
                        "There was an error downloading the file %s", file.path
                    )
                    continue

                local_file_path = "{}/{}".format(hacs_directory, file.name)
                with open(
                    local_file_path, "w", encoding="utf-8", errors="ignore"
                ) as outfile:
                    outfile.write(filecontent)
                    outfile.close()

        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error(
                "This sucks! There was an issue downloading 'hacs' - %s", error
            )

        # Download the content of "frontend"
        try:
            remote_dir = repo.get_dir_contents("custom_components/hacs/frontend", ref)
            local_base_dir = "{}/frontend".format(hacs_directory)

            _LOGGER.debug("Content in remote repo %s", str(list(remote_dir)))

            # Create dir if it does not exist.
            if not os.path.exists(local_base_dir):
                os.mkdir(local_base_dir)

            for file in remote_dir:
                if file.type == "dir":
                    _LOGGER.debug("%s is a directory, skipping.", file.name)
                    continue
                _LOGGER.debug("Downloading %s", file.path)

                filecontent = await async_download_file(hass, file.download_url)
                if filecontent is None:
                    _LOGGER.error(
                        "There was an error downloading the file %s", file.path
                    )
                    continue

                local_file_path = "{}/{}".format(local_base_dir, file.name)
                with open(
                    local_file_path, "w", encoding="utf-8", errors="ignore"
                ) as outfile:
                    outfile.write(filecontent)
                    outfile.close()
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error(
                "This sucks! There was an issue downloading 'frontend' - %s", error
            )

        # Download the content of "frontend/views"
        try:
            remote_dir = repo.get_dir_contents(
                "custom_components/hacs/frontend/views", ref
            )
            local_base_dir = "{}/frontend/views".format(hacs_directory)

            _LOGGER.debug("Content in remote repo %s", str(list(remote_dir)))

            # Create dir if it does not exist.
            if not os.path.exists(local_base_dir):
                os.mkdir(local_base_dir)

            for file in remote_dir:
                if file.type == "dir":
                    _LOGGER.debug("%s is a directory, skipping.", file.name)
                    continue
                _LOGGER.debug("Downloading %s", file.path)

                filecontent = await async_download_file(hass, file.download_url)
                if filecontent is None:
                    _LOGGER.error(
                        "There was an error downloading the file %s", file.path
                    )
                    continue

                local_file_path = "{}/{}".format(local_base_dir, file.name)
                with open(
                    local_file_path, "w", encoding="utf-8", errors="ignore"
                ) as outfile:
                    outfile.write(filecontent)
                    outfile.close()
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error(
                "This sucks! There was an issue downloading 'frontend/views' - %s",
                error,
            )

        # Download the content of "frontend/elements"
        try:
            remote_dir = repo.get_dir_contents(
                "custom_components/hacs/frontend/elements", ref
            )
            local_base_dir = "{}/frontend/elements".format(hacs_directory)

            _LOGGER.debug("Content in remote repo %s", str(list(remote_dir)))

            # Create dir if it does not exist.
            if not os.path.exists(local_base_dir):
                os.mkdir(local_base_dir)

            for file in remote_dir:
                if file.type == "dir":
                    _LOGGER.debug("%s is a directory, skipping.", file.name)
                    continue
                _LOGGER.debug("Downloading %s", file.path)

                filecontent = await async_download_file(hass, file.download_url)
                if filecontent is None:
                    _LOGGER.error(
                        "There was an error downloading the file %s", file.path
                    )
                    continue

                local_file_path = "{}/{}".format(local_base_dir, file.name)
                with open(
                    local_file_path, "w", encoding="utf-8", errors="ignore"
                ) as outfile:
                    outfile.write(filecontent)
                    outfile.close()
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error(
                "This sucks! There was an issue downloading 'frontend/elements' - %s",
                error,
            )

        # Download the content of "handler"
        try:
            remote_dir = repo.get_dir_contents("custom_components/hacs/handler", ref)
            local_base_dir = "{}/handler".format(hacs_directory)

            _LOGGER.debug("Content in remote repo %s", str(list(remote_dir)))

            # Create dir if it does not exist.
            if not os.path.exists(local_base_dir):
                os.mkdir(local_base_dir)

            for file in remote_dir:
                _LOGGER.debug("Downloading %s", file.path)

                filecontent = await async_download_file(hass, file.download_url)
                if filecontent is None:
                    _LOGGER.error(
                        "There was an error downloading the file %s", file.path
                    )
                    continue

                local_file_path = "{}/{}".format(local_base_dir, file.name)
                with open(
                    local_file_path, "w", encoding="utf-8", errors="ignore"
                ) as outfile:
                    outfile.write(filecontent)
                    outfile.close()
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.error(
                "This sucks! There was an issue downloading 'handler' - %s", error
            )

        # Update hass.data
        hass.data[DOMAIN_DATA]["hacs"]["local"] = hass.data[DOMAIN_DATA]["hacs"][
            "remote"
        ]
        hass.data[DOMAIN_DATA]["hacs"]["restart_pending"] = True
        await write_to_data_store(hass.config.path(), hass.data[DOMAIN_DATA])

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.error("This sucks! There was an issue downloading HACS - %s", error)
