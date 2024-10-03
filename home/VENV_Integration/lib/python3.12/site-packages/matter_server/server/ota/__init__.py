"""OTA implementation for the Matter Server."""

import asyncio
import json
from logging import LoggerAdapter
from pathlib import Path

from matter_server.common.models import UpdateSource
from matter_server.server.ota import dcl

_local_updates: dict[tuple[int, int], dict] = {}


async def load_local_updates(ota_provider_dir: Path) -> None:
    """Load updates from locally stored json files."""

    def _load_update(ota_provider_dir: Path) -> None:
        if not ota_provider_dir.exists():
            return
        for update_file in ota_provider_dir.glob("*.json"):
            with open(update_file) as f:
                update = json.load(f)
                model_version = update["modelVersion"]
                _local_updates[(model_version["vid"], model_version["pid"])] = (
                    model_version
                )

    await asyncio.get_running_loop().run_in_executor(
        None, _load_update, ota_provider_dir
    )


async def check_for_update(
    logger: LoggerAdapter,
    vid: int,
    pid: int,
    current_software_version: int,
    requested_software_version: int | str | None = None,
) -> tuple[UpdateSource, dict] | tuple[None, None]:
    """Check for software updates."""
    if (vid, pid) in _local_updates:
        local_update = _local_updates[(vid, pid)]
        if (
            requested_software_version is None
            or local_update["softwareVersion"] == requested_software_version
            or local_update["softwareVersionString"] == requested_software_version
        ):
            return UpdateSource.LOCAL, local_update

    if dcl_update := await dcl.check_for_update(
        logger, vid, pid, current_software_version, requested_software_version
    ):
        return UpdateSource.MAIN_NET_DCL, dcl_update
    return None, None
