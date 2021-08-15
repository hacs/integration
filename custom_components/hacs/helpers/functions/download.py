"""Helpers to download repository content."""
import os
import pathlib
import tempfile
import zipfile

import async_timeout
import backoff
from queueman import QueueManager, concurrent

from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.helpers.functions.filters import (
    filter_content_return_one_of_type,
)
from custom_components.hacs.helpers.functions.save import async_save_file
from custom_components.hacs.share import get_hacs
from custom_components.hacs.utils.logger import getLogger

_LOGGER = getLogger()


class FileInformation:
    def __init__(self, url, path, name):
        self.download_url = url
        self.path = path
        self.name = name


@backoff.on_exception(backoff.expo, Exception, max_tries=5)
async def async_download_file(url):
    """Download files, and return the content."""
    hacs = get_hacs()
    if url is None:
        return

    if "tags/" in url:
        url = url.replace("tags/", "")

    _LOGGER.debug("Downloading %s", url)

    result = None

    with async_timeout.timeout(60, loop=hacs.hass.loop):
        request = await hacs.session.get(url)

        # Make sure that we got a valid result
        if request.status == 200:
            result = await request.read()
        else:
            raise HacsException(
                "Got status code {} when trying to download {}".format(
                    request.status, url
                )
            )

    return result


def should_try_releases(repository):
    """Return a boolean indicating whether to download releases or not."""
    if repository.data.zip_release:
        if repository.data.filename.endswith(".zip"):
            if repository.ref != repository.data.default_branch:
                return True
    if repository.ref == repository.data.default_branch:
        return False
    if repository.data.category not in ["plugin", "theme"]:
        return False
    if not repository.data.releases:
        return False
    return True


def gather_files_to_download(repository):
    """Return a list of file objects to be downloaded."""
    files = []
    tree = repository.tree
    ref = f"{repository.ref}".replace("tags/", "")
    releaseobjects = repository.releases.objects
    category = repository.data.category
    remotelocation = repository.content.path.remote

    if should_try_releases(repository):
        for release in releaseobjects or []:
            if ref == release.tag_name:
                for asset in release.assets or []:
                    files.append(asset)
        if files:
            return files

    if repository.content.single:
        for treefile in tree:
            if treefile.filename == repository.data.file_name:
                files.append(
                    FileInformation(
                        treefile.download_url, treefile.full_path, treefile.filename
                    )
                )
        return files

    if category == "plugin":
        for treefile in tree:
            if treefile.path in ["", "dist"]:
                if remotelocation == "dist" and not treefile.filename.startswith(
                    "dist"
                ):
                    continue
                if not remotelocation:
                    if not treefile.filename.endswith(".js"):
                        continue
                    if treefile.path != "":
                        continue
                if not treefile.is_directory:
                    files.append(
                        FileInformation(
                            treefile.download_url, treefile.full_path, treefile.filename
                        )
                    )
        if files:
            return files

    if repository.data.content_in_root:
        if not repository.data.filename:
            if category == "theme":
                tree = filter_content_return_one_of_type(
                    repository.tree, "", "yaml", "full_path"
                )

    for path in tree:
        if path.is_directory:
            continue
        if path.full_path.startswith(repository.content.path.remote):
            files.append(
                FileInformation(path.download_url, path.full_path, path.filename)
            )
    return files


async def download_zip_files(repository, validate):
    """Download ZIP archive from repository release."""
    contents = []
    queue = QueueManager()
    try:
        for release in repository.releases.objects:
            repository.logger.info(
                f"ref: {repository.ref}  ---  tag: {release.tag_name}"
            )
            if release.tag_name == repository.ref.split("/")[1]:
                contents = release.assets

        if not contents:
            return validate

        for content in contents or []:
            queue.add(async_download_zip_file(repository, content, validate))

        await queue.execute()
    except (Exception, BaseException) as exception:  # pylint: disable=broad-except
        validate.errors.append(f"Download was not completed [{exception}]")

    return validate


async def async_download_zip_file(repository, content, validate):
    """Download ZIP archive from repository release."""
    try:
        filecontent = await async_download_file(content.download_url)

        if filecontent is None:
            validate.errors.append(f"[{content.name}] was not downloaded.")
            return

        result = await async_save_file(
            f"{tempfile.gettempdir()}/{repository.data.filename}", filecontent
        )
        with zipfile.ZipFile(
            f"{tempfile.gettempdir()}/{repository.data.filename}", "r"
        ) as zip_file:
            zip_file.extractall(repository.content.path.local)

        os.remove(f"{tempfile.gettempdir()}/{repository.data.filename}")

        if result:
            repository.logger.info(f"Download of {content.name} completed")
            return
        validate.errors.append(f"[{content.name}] was not downloaded.")
    except (Exception, BaseException) as exception:  # pylint: disable=broad-except
        validate.errors.append(f"Download was not completed [{exception}]")

    return validate


async def download_content(repository):
    """Download the content of a directory."""
    queue = QueueManager()
    contents = gather_files_to_download(repository)
    repository.logger.debug(repository.data.filename)
    if not contents:
        raise HacsException("No content to download")

    for content in contents:
        if repository.data.content_in_root and repository.data.filename:
            if content.name != repository.data.filename:
                continue
        queue.add(dowload_repository_content(repository, content))
    await queue.execute()
    return repository.validate


@concurrent(10)
async def dowload_repository_content(repository, content):
    """Download content."""
    try:
        repository.logger.debug(f"Downloading {content.name}")

        filecontent = await async_download_file(content.download_url)

        if filecontent is None:
            repository.validate.errors.append(f"[{content.name}] was not downloaded.")
            return

        # Save the content of the file.
        if repository.content.single or content.path is None:
            local_directory = repository.content.path.local

        else:
            _content_path = content.path
            if not repository.data.content_in_root:
                _content_path = _content_path.replace(
                    f"{repository.content.path.remote}", ""
                )

            local_directory = f"{repository.content.path.local}/{_content_path}"
            local_directory = local_directory.split("/")
            del local_directory[-1]
            local_directory = "/".join(local_directory)

        # Check local directory
        pathlib.Path(local_directory).mkdir(parents=True, exist_ok=True)

        local_file_path = (f"{local_directory}/{content.name}").replace("//", "/")

        result = await async_save_file(local_file_path, filecontent)
        if result:
            repository.logger.info(f"Download of {content.name} completed")
            return
        repository.validate.errors.append(f"[{content.name}] was not downloaded.")

    except (Exception, BaseException) as exception:  # pylint: disable=broad-except
        repository.validate.errors.append(f"Download was not completed [{exception}]")
