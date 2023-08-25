"""Generate HACS compliant data."""
from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging
import os
import sys
from typing import Any, Literal

from aiogithubapi import (
    GitHub,
    GitHubAPI,
    GitHubException,
    GitHubNotFoundException,
    GitHubNotModifiedException,
    GitHubReleaseModel,
)
from aiohttp import ClientSession
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.json import JSONEncoder

from custom_components.hacs.base import HacsBase, HacsRepositories
from custom_components.hacs.const import HACS_ACTION_GITHUB_API_HEADERS
from custom_components.hacs.data_client import HacsDataClient
from custom_components.hacs.exceptions import HacsExecutionStillInProgress
from custom_components.hacs.repositories.base import (
    HACS_MANIFEST_KEYS_TO_EXPORT,
    REPOSITORY_KEYS_TO_EXPORT,
    HacsRepository,
)
from custom_components.hacs.utils.data import HacsData
from custom_components.hacs.utils.decorator import concurrent
from custom_components.hacs.utils.queue_manager import QueueManager

logging.addLevelName(logging.DEBUG, "")
logging.addLevelName(logging.INFO, "")
logging.addLevelName(logging.ERROR, "::error::")
logging.addLevelName(logging.WARNING, "::warning::")

log_handler = logging.getLogger("custom_components.hacs")
log_handler.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(logging.Formatter("%(levelname)s%(message)s"))
log_handler.addHandler(stream_handler)

OUTPUT_DIR = os.path.join(os.getcwd(), "outputdata")


def repository_has_missing_keys(
    repository: HacsRepository,
    stage: Literal["update"] | Literal["store"],
) -> bool:
    """Check if repository has missing keys."""
    retval = False

    def _do_log(msg: str) -> None:
        repository.logger.log(
            logging.WARNING if stage == "update" else logging.ERROR,
            "%s[%s] %s",
            repository.string,
            stage,
            msg,
        )

    if repository.data.last_commit is None and repository.data.last_version is None:
        retval = True
        _do_log("Missing version data")
    if repository.data.category == "integration" and repository.data.domain is None:
        retval = True
        _do_log("Missing domain")

    return retval


class AdjustedHacsData(HacsData):
    """Extended HACS data."""

    async def register_base_data(
        self,
        category: str,
        repositories: dict[str, dict[str, Any]],
        removed: list[str],
    ):
        """Restore saved data."""
        await self.register_unknown_repositories(repositories, category)
        for entry, repo_data in repositories.items():
            if repo_data["full_name"] in removed:
                self.hacs.log.warning(
                    "Skipping %s as it's removed from HACS", repo_data["full_name"]
                )
                continue
            self.async_restore_repository(entry, repo_data)

    @callback
    def async_store_repository_data(self, repository: HacsRepository) -> dict:
        """Store the repository data."""
        data = {"manifest": {}}
        for key, default in HACS_MANIFEST_KEYS_TO_EXPORT:
            if (value := getattr(repository.repository_manifest, key, default)) != default:
                data["manifest"][key] = value

        for key, default in REPOSITORY_KEYS_TO_EXPORT:
            if (value := getattr(repository.data, key, default)) != default:
                data[key] = value

        data["last_fetched"] = (
            repository.data.last_fetched.timestamp()
            if repository.data.last_fetched
            else datetime.utcnow().timestamp()
        )

        if not repository_has_missing_keys(repository, "store"):
            self.content[str(repository.data.id)] = data


class AdjustedHacs(HacsBase):
    """Extended HACS class."""

    data: AdjustedHacsData

    def __init__(self, session: ClientSession, *, token: str | None = None):
        """Initialize."""
        super().__init__()
        try:
            self.hass = HomeAssistant()  # pylint: disable=no-value-for-parameter
        except TypeError:
            self.hass = HomeAssistant("")  # pylint: disable=too-many-function-args

        self.queue = QueueManager(self.hass)
        self.repositories = HacsRepositories()
        self.system.generator = True
        self.session = session
        self.core.config_path = None
        self.configuration.token = token
        self.configuration.experimental = True
        self.data = AdjustedHacsData(hacs=self)
        self.data_client = HacsDataClient(session=session, client_name="HACS/Generator")

        self.github = GitHub(
            token,
            session,
            headers=HACS_ACTION_GITHUB_API_HEADERS,
        )
        self.githubapi = GitHubAPI(
            token=token,
            session=session,
            **{"client_name": "HACS/Generator"},
        )

    async def async_can_update(self) -> int:
        """Helper to calculate the number of repositories we can fetch data for."""
        if not os.getenv("DATA_GENERATOR_TOKEN"):
            return 10
        return await super().async_can_update()

    @concurrent(concurrenttasks=10)
    async def concurrent_register_repository(
        self,
        repository_full_name: str,
        category: str,
    ) -> None:
        """Register a repository."""
        await self.async_register_repository(
            repository_full_name=repository_full_name, category=category, default=True
        )

    @concurrent(concurrenttasks=10, backoff_time=0.1)
    async def concurrent_update_repository(self, repository: HacsRepository) -> None:
        """Update a repository."""
        if repository_has_missing_keys(repository, "update"):
            # If we have missing keys, force a full update by setting the etag to None
            repository.data.etag_repository = None

        if repository.data.last_version not in (None, ""):
            try:
                repository.logger.info("%s Fetching repository releases", repository.string)
                response = await self.githubapi.generic(
                    endpoint=f"/repos/{repository.data.full_name}/releases/latest",
                    etag=repository.data.etag_releases,
                )
                response.data = GitHubReleaseModel(response.data) if response.data else None
                repository.data.etag_releases = response.etag
                if (releases := response.data) is not None:
                    repository.data.releases = True
                    repository.releases.objects = [releases]
                    repository.data.published_tags = [
                        x.tag_name for x in repository.releases.objects
                    ]
                    if (
                        next_version := next(iter(repository.data.published_tags), None)
                    ) != repository.data.last_version:
                        repository.data.last_version = next_version
                        repository.data.etag_repository = None

            except GitHubNotModifiedException:
                repository.data.releases = True
                repository.logger.info("%s Release data is up to date", repository.string)
            except GitHubNotFoundException:
                repository.data.releases = False
                repository.logger.info("%s No releases found", repository.string)
            except GitHubException as exception:
                repository.data.releases = False
                repository.logger.warning("%s %s", repository.string, exception)

        await repository.common_update(
            force=repository.data.etag_repository is None,
            skip_releases=repository.data.releases,
        )

    async def generate_data_for_category(
        self,
        category: str,
        repository_name: str | None,
        current_data: dict[str, dict[str, Any]],
        force: bool,
    ) -> dict[str, dict[str, Any]]:
        """Generate data for category."""
        removed = (
            []
            if repository_name is not None
            else await self.data_client.get_repositories("removed")
        )
        await self.data.register_base_data(
            category,
            {} if force else current_data,
            removed,
        )
        self.queue.clear()
        await self.get_category_repositories(category, repository_name, removed)

        async def _handle_queue():
            if not self.queue.pending_tasks:
                return
            can_update = await self.async_can_update()
            self.log.debug(
                "Can update %s repositories, %s items in queue",
                can_update,
                self.queue.pending_tasks,
            )
            if can_update == 0:
                self.log.info("Can't do anything, sleeping for 1 min.")
                await asyncio.sleep(60)
                await _handle_queue()

            try:
                await self.queue.execute(round(can_update / (6 if force else 3)) or 1)
            except HacsExecutionStillInProgress:
                return

            await _handle_queue()

        await _handle_queue()

        self.data.content = {}
        for repository in self.repositories.list_all:
            if repository.data.category != category:
                continue
            if repository.data.archived:
                continue
            self.data.async_store_repository_data(repository)

        return self.data.content

    async def get_category_repositories(
        self,
        category: str,
        repository_name: str | None,
        removed: list[str],
    ) -> None:
        """Get repositories from category."""
        repositories = (
            await self.async_github_get_hacs_default_file(category)
            if repository_name is None
            else []
        )

        if repository_name is not None:
            repositories = [repository_name]
        elif category == "integration":
            # hacs/integration i not in the default file, but it's still needed
            repositories.append("hacs/integration")

        for repo in repositories:
            if repo in removed:
                self.log.warning("Skipping %s as it's removed from HACS", repo)
                continue
            repository = self.repositories.get_by_full_name(repo)
            if repository is not None:
                self.queue.add(self.concurrent_update_repository(repository=repository))
                continue

            self.queue.add(
                self.concurrent_register_repository(
                    repository_full_name=repo,
                    category=category,
                )
            )

    async def summarize_data(
        self,
        current_data: dict[str, dict[str, Any]],
        updated_data: dict[str, dict[str, Any]],
    ) -> int:
        """Summarize data."""
        changed = 0

        for repo_id, repo_data in updated_data.items():
            if repo_data.get("etag_releases") != current_data.get(repo_id, {}).get(
                "etag_releases"
            ) or repo_data.get("etag_repository") != current_data.get(repo_id, {}).get(
                "etag_repository"
            ):
                changed += 1

        print(
            json.dumps(
                (
                    {
                        "rate_limit": (
                            await self.githubapi.rate_limit()
                        ).data.resources.core.as_dict,
                        "current_count": len(current_data.keys()),
                        "new_count": len(updated_data.keys()),
                        "changed": changed,
                    }
                    if len(updated_data) > 1
                    else updated_data
                ),
                indent=2,
            )
        )
        return changed


async def generate_category_data(category: str, repository_name: str = None):
    """Generate data."""
    async with ClientSession() as session:
        hacs = AdjustedHacs(session=session, token=os.getenv("DATA_GENERATOR_TOKEN"))
        os.makedirs(os.path.join(OUTPUT_DIR, category), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "diff"), exist_ok=True)
        force = os.environ.get("FORCE_REPOSITORY_UPDATE") == "True"
        stored_data = await hacs.data_client.get_data(category)
        current_data = (
            next(
                (
                    {key: value}
                    for key, value in stored_data.items()
                    if value["full_name"] == repository_name
                ),
                {},
            )
            if repository_name is not None
            else stored_data
        )

        updated_data = await hacs.generate_data_for_category(
            category, repository_name, current_data, force=force
        )

        changed = await hacs.summarize_data(current_data, updated_data)
        if (
            not force
            and changed == 0
            and repository_name is None
            and len(current_data) == len(updated_data)
        ):
            print("No changes, exiting")
            return

        with open(
            os.path.join(OUTPUT_DIR, category, "data.json"),
            mode="w",
            encoding="utf-8",
        ) as data_file:
            json.dump(
                updated_data,
                data_file,
                cls=JSONEncoder,
                separators=(",", ":"),
            )
        with open(
            os.path.join(OUTPUT_DIR, category, "repositories.json"),
            mode="w",
            encoding="utf-8",
        ) as repositories_file:
            json.dump(
                [v["full_name"] for v in updated_data.values()],
                repositories_file,
                separators=(",", ":"),
                sort_keys=True,
            )

        with open(
            os.path.join(OUTPUT_DIR, "diff", f"{category}_before.json"),
            mode="w",
            encoding="utf-8",
        ) as data_file:
            json.dump(
                current_data,
                data_file,
                cls=JSONEncoder,
                sort_keys=True,
                indent=2,
            )

        with open(
            os.path.join(OUTPUT_DIR, "diff", f"{category}_after.json"),
            mode="w",
            encoding="utf-8",
        ) as data_file:
            json.dump(
                updated_data,
                data_file,
                cls=JSONEncoder,
                sort_keys=True,
                indent=2,
            )


if __name__ == "__main__":
    asyncio.run(
        generate_category_data(
            sys.argv[1],  # category
            sys.argv[2] if len(sys.argv) > 2 else None,  # repository_name
        )
    )
