"""Download."""
import logging
import os
import aiofiles

import async_timeout

from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger('custom_components.hacs')


async def async_download_file(hass, url):
    """
    Download files, and return the content.
    """
    # There is a bug somewhere... TODO: Find that bug....
    if "tags/" in url:
        url = url.replace("tags/", "")

    _LOGGER.debug("Donwloading %s", url)

    result = None

    try:
        with async_timeout.timeout(5, loop=hass.loop):
            request = await async_get_clientsession(hass).get(url)

            # Make sure that we got a valid result
            if request.status == 200:
                result = await request.text()
            else:
                _LOGGER.debug(
                    "Got status code %s when trying to download %s", request.status, url
                )

    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.debug("Downloading %s failed with %s", url, error)

    return result


async def async_save_file(location, content):
    """Save files."""
    if "-bundle" in location:
        location = location.replace("-bundle", "")

    _LOGGER.debug("Saving %s", location)

    try:
        async with aiofiles.open(location, mode='w', encoding="utf-8", errors="ignore") as outfile:
            await outfile.write(content)
            outfile.close()

    except Exception as error:  # pylint: disable=broad-except
        msg = "Could not write data to {} - {}".format(location, error)
        _LOGGER.debug(msg)


async def download_hacs(hass):
    """
    Special function to update HACS.
    """
    git = data["commander"].github
    hacs_directory = "{}/custom_components/hacs".format(hass.config.path())

    try:
        repo = git.get_repo("custom-components/hacs")
        ref = "tags/{}".format(data["hacs"]["remote"])

        remote_dir = repo.get_contents("custom_components/hacs", ref)

        _LOGGER.debug("Content in remote repo %s", str(list(remote_dir)))

        # Download the content of "hacs"
        try:
            for file in remote_dir:
                # We download sub dirs at a later stage.
                if file.type == "dir":
                    _LOGGER.debug("%s is a directory, skipping.", file.name)
                    continue

                _LOGGER.debug("Downloading %s", file.path)

                filecontent = await async_download_file(hass, file.download_url)
                if filecontent is None:
                    _LOGGER.debug(
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
            _LOGGER.debug(
                "This sucks! There was an issue downloading 'hacs' - %s", error
            )

        # Download the content of "frontend"
        try:
            remote_dir = repo.get_contents("custom_components/hacs/frontend", ref)
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
                    _LOGGER.debug(
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
            _LOGGER.debug(
                "This sucks! There was an issue downloading 'frontend' - %s", error
            )

        # Download the content of "frontend/views"
        try:
            remote_dir = repo.get_contents(
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
                    _LOGGER.debug(
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
            _LOGGER.debug(
                "This sucks! There was an issue downloading 'frontend/views' - %s",
                error,
            )

        # Download the content of "frontend/elements"
        try:
            remote_dir = repo.get_contents(
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
                    _LOGGER.debug(
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
            _LOGGER.debug(
                "This sucks! There was an issue downloading 'frontend/elements' - %s",
                error,
            )

        # Download the content of "handler"
        try:
            remote_dir = repo.get_contents("custom_components/hacs/handler", ref)
            local_base_dir = "{}/handler".format(hacs_directory)

            _LOGGER.debug("Content in remote repo %s", str(list(remote_dir)))

            # Create dir if it does not exist.
            if not os.path.exists(local_base_dir):
                os.mkdir(local_base_dir)

            for file in remote_dir:
                _LOGGER.debug("Downloading %s", file.path)

                filecontent = await async_download_file(hass, file.download_url)
                if filecontent is None:
                    _LOGGER.debug(
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
            _LOGGER.debug(
                "This sucks! There was an issue downloading 'handler' - %s", error
            )

        # Update hass.data
        data["hacs"]["local"] = data["hacs"][
            "remote"
        ]
        data["hacs"]["pending_restart"] = True


    except Exception as error:  # pylint: disable=broad-except
        _LOGGER.debug("This sucks! There was an issue downloading HACS - %s", error)
