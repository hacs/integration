"""Handle OTA software version endpoints of the DCL."""

from http import HTTPStatus
import logging
from typing import Any, cast

from aiohttp import ClientError, ClientSession

from matter_server.common.errors import UpdateCheckError
from matter_server.server.helpers import DCL_PRODUCTION_URL


async def _get_software_versions(session: ClientSession, vid: int, pid: int) -> Any:
    """Check DCL if there are updates available for a particular node."""
    # fetch the paa certificates list
    async with session.get(f"/dcl/model/versions/{vid}/{pid}") as response:
        if response.status == HTTPStatus.NOT_FOUND:
            return None
        response.raise_for_status()
        return await response.json()


async def _get_software_version(
    session: ClientSession, vid: int, pid: int, software_version: int
) -> Any:
    """Check DCL if there are updates available for a particular node."""
    # fetch the paa certificates list
    async with session.get(
        f"/dcl/model/versions/{vid}/{pid}/{software_version}"
    ) as response:
        response.raise_for_status()
        return await response.json()


async def _check_update_version(
    session: ClientSession,
    vid: int,
    pid: int,
    current_software_version: int,
    requested_software_version: int,
    requested_software_version_string: str | None = None,
) -> None | dict:
    version_res: dict = await _get_software_version(
        session, vid, pid, requested_software_version
    )
    if not isinstance(version_res, dict):
        raise TypeError("Unexpected DCL response.")

    if "modelVersion" not in version_res:
        raise ValueError("Unexpected DCL response.")

    version_candidate: dict = cast(dict, version_res["modelVersion"])

    # If we are looking for a specific version by string, check if it matches
    if (
        requested_software_version_string is not None
        and version_candidate["softwareVersionString"]
        != requested_software_version_string
    ):
        return None

    if version_candidate["softwareVersionValid"] is False:
        return None

    if version_candidate["otaUrl"].strip() == "":
        return None

    # Check minApplicableSoftwareVersion/maxApplicableSoftwareVersion
    min_sw_version = version_candidate["minApplicableSoftwareVersion"]
    max_sw_version = version_candidate["maxApplicableSoftwareVersion"]
    if (
        current_software_version < min_sw_version
        or current_software_version > max_sw_version
    ):
        return None

    return version_candidate


async def check_for_update(
    logger: logging.LoggerAdapter,
    vid: int,
    pid: int,
    current_software_version: int,
    requested_software_version: int | str | None = None,
) -> None | dict:
    """Check if there is a software update available on the DCL."""
    try:
        async with ClientSession(
            base_url=DCL_PRODUCTION_URL, raise_for_status=False
        ) as session:
            # If a specific version as integer is requested, just fetch it (and hope it exists)
            if isinstance(requested_software_version, int):
                return await _check_update_version(
                    session,
                    vid,
                    pid,
                    current_software_version,
                    requested_software_version,
                )

            # Get all versions and check each one of them.
            versions = await _get_software_versions(session, vid, pid)
            if versions is None:
                logger.info(
                    "There is no update information for this device on the DCL."
                )
                return None

            all_software_versions: list[int] = versions["modelVersions"][
                "softwareVersions"
            ]
            newer_software_versions = [
                version
                for version in all_software_versions
                if version > current_software_version
            ]

            # Check if there is a newer software version available, no downgrade possible
            if not newer_software_versions:
                return None

            # Check if latest firmware is applicable, and backtrack from there
            for version in sorted(newer_software_versions, reverse=True):
                if version_candidate := await _check_update_version(
                    session,
                    vid,
                    pid,
                    current_software_version,
                    version,
                    requested_software_version,
                ):
                    return version_candidate
                logger.debug("Software version %d not applicable.", version)
            return None

    except (ClientError, TimeoutError) as err:
        raise UpdateCheckError(
            f"Fetching software versions from DCL for device with vendor id {vid} product id {pid} failed."
        ) from err
