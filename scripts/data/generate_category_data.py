"""Generate HACS compliant data."""
import asyncio
from datetime import datetime
import json
import logging
import os
import sys
from typing import Any

from aiogithubapi import GitHub, GitHubAPI
from aiohttp import ClientSession
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.json import JSONEncoder

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import HACS_ACTION_GITHUB_API_HEADERS
from custom_components.hacs.data_client import HacsDataClient
from custom_components.hacs.exceptions import HacsExecutionStillInProgress
from custom_components.hacs.repositories.base import HacsRepository
from custom_components.hacs.utils.data import HacsData
from custom_components.hacs.utils.decorator import concurrent
from custom_components.hacs.utils.queue_manager import QueueManager

log_handler = logging.getLogger("custom_components.hacs")
log_handler.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.DEBUG)
stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
log_handler.addHandler(stream_handler)

OUTPUT_DIR = os.path.join(os.getcwd(), "outputdata")

REPOSITORY_KEYS_TO_EXPORT = (
    # Keys can not be removed from this list until v3
    # If keys are added, the action need to be re-run with force
    ("description", ""),
    ("downloads", 0),
    ("domain", None),
    ("etag_repository", None),
    ("full_name", ""),
    ("last_commit", None),
    ("last_updated", 0),
    ("last_version", None),
    ("manifest_name", None),
    ("open_issues", 0),
    ("pushed_at", ""),
    ("stargazers_count", 0),
    ("topics", []),
)

HACS_MANIFEST_KEYS_TO_EXPORT = (
    # Keys can not be removed from this list until v3
    # If keys are added, the action need to be re-run with force
    ("country", []),
    ("name", None),
)


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
                self.hacs.log.info("Skipping %s as it's removed from HACS", repo_data["full_name"])
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

        self.content[str(repository.data.id)] = data


class AdjustedHacs(HacsBase):
    """Extended HACS class."""

    data: AdjustedHacsData

    def __init__(self, session: ClientSession, *, token: str | None = None):
        """Initialize."""
        super().__init__()
        self.hass = HomeAssistant()
        self.queue = QueueManager(self.hass)
        self.session = session
        self.core.config_path = None
        self.configuration.token = token
        self.configuration.experimental = True
        self.data = AdjustedHacsData(hacs=self)
        self.data_client = HacsDataClient(session=session)

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

    @concurrent(concurrenttasks=10, backoff_time=2)
    async def update_repository(self, repository: HacsRepository) -> None:
        """Update a repository."""
        await repository.common_update()

    async def generate_data_for_category(
        self,
        category: str,
        force: bool,
    ) -> dict[str, dict[str, Any]]:
        """Generate data for category."""
        removed = await self.data_client.get_repositories("removed")
        await self.data.register_base_data(
            category,
            {} if force else await self.data_client.get_data(category),
            removed,
        )
        self.queue.clear()
        await self.get_category_repositories(category, removed)

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
                await self.queue.execute(round(can_update / 6) or 1)
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
        removed: list[str],
    ) -> None:
        """Get repositories from category."""
        repositories = await self.async_github_get_hacs_default_file(category)

        for repo in repositories:
            if repo in removed:
                self.log.info("Skipping %s as it's removed from HACS", repo)
                continue
            repository = self.repositories.get_by_full_name(repo)
            if repository is not None:
                self.queue.add(self.update_repository(repository=repository))
                continue

            self.queue.add(
                self.async_register_repository(
                    repository_full_name=repo,
                    category=category,
                    default=True,
                )
            )


async def generate_category_data(category: str):
    """Generate data."""
    async with ClientSession() as session:
        hacs = AdjustedHacs(session=session, token=os.getenv("DATA_GENERATOR_TOKEN"))
        os.makedirs(os.path.join(OUTPUT_DIR, category), exist_ok=True)
        data = await hacs.generate_data_for_category(
            category,
            force=os.environ.get("FORCE_REPOSITORY_UPDATE") == "True",
        )

        with open(
            os.path.join(OUTPUT_DIR, category, "data.json"),
            mode="w",
            encoding="utf-8",
        ) as data_file:
            json.dump(
                data,
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
                [v["full_name"] for v in data.values()],
                repositories_file,
                separators=(",", ":"),
            )

        print((await hacs.githubapi.rate_limit()).data.resources.core.as_dict)


if __name__ == "__main__":
    asyncio.run(generate_category_data(sys.argv[1]))
