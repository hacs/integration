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
import voluptuous as vol

from custom_components.hacs.base import HacsBase, HacsRepositories
from custom_components.hacs.const import HACS_ACTION_GITHUB_API_HEADERS
from custom_components.hacs.data_client import HacsDataClient
from custom_components.hacs.enums import HacsGitHubRepo
from custom_components.hacs.exceptions import HacsExecutionStillInProgress
from custom_components.hacs.repositories.base import (
    HACS_MANIFEST_KEYS_TO_EXPORT,
    REPOSITORY_KEYS_TO_EXPORT,
    HacsRepository,
)
from custom_components.hacs.utils.data import HacsData
from custom_components.hacs.utils.decode import decode_content
from custom_components.hacs.utils.decorator import concurrent
from custom_components.hacs.utils.json import json_loads
from custom_components.hacs.utils.queue_manager import QueueManager
from custom_components.hacs.utils.validate import VALIDATE_GENERATED_V2_REPO_DATA

from .common import expand_and_humanize_error, print_error_and_exit

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
COMPARE_IGNORE = {"etag_releases", "etag_repository", "last_fetched"}


def jsonprint(data: any):
    print(
        json.dumps(
            data,
            cls=JSONEncoder,
            sort_keys=True,
            indent=2,
        )
    )


def dicts_are_equal(a: dict, b: dict, ignore: set[str]) -> bool:
    def _dumper(obj: dict):
        return json.dumps(
            {k: v for k, v in obj.items() if k not in ignore},
            sort_keys=True,
            cls=JSONEncoder,
        )

    return _dumper(a) == _dumper(b)


def repository_has_missing_keys(
    repository: HacsRepository,
    stage: Literal["update", "store"],
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
            if (
                value := getattr(repository.repository_manifest, key, default)
            ) != default:
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
        self.hass = HomeAssistant("")  # pylint: disable=too-many-function-args

        self.queue = QueueManager(self.hass)
        self.repositories = HacsRepositories()
        self.system.generator = True
        self.session = session
        self.core.config_path = None
        self.configuration.token = token
        self.data = AdjustedHacsData(hacs=self)
        self.data_client = HacsDataClient(
            session=session, client_name="HACS/Generator")

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
            releases: list[GitHubReleaseModel] = []
            try:
                repository.logger.info(
                    "%s Fetching repository releases",
                    repository.string,
                )
                response = await self.githubapi.generic(
                    endpoint=f"/repos/{repository.data.full_name}/releases",
                    etag=repository.data.etag_releases,
                    kwargs={"per_page": 30},
                )
                releases = [GitHubReleaseModel(rel) for rel in response.data]
                release_count = len(releases)

                repository.data.etag_releases = response.etag
                repository.data.prerelease = None

                if release_count != 0:
                    for release in releases:
                        if release.draft:
                            repository.logger.warning(
                                "%s Found draft %s", repository.string, release.tag_name)

                        elif release.prerelease:
                            repository.logger.info(
                                "%s Found prerelease %s", repository.string, release.tag_name)
                            if repository.data.prerelease is None:
                                repository.data.prerelease = release.tag_name

                        else:
                            repository.logger.info(
                                "%s Found release %s", repository.string, release.tag_name)
                            repository.data.releases = True
                            repository.releases.objects = releases
                            repository.data.published_tags = [
                                x.tag_name for x in repository.releases.objects
                            ]
                            if repository.data.last_version != release.tag_name:
                                repository.data.last_version = release.tag_name
                                repository.data.etag_repository = None
                            break

                if release_count >= 30 and not repository.data.releases:
                    repository.logger.warning(
                        "%s Found 30 releases but no release, falling back to fetching latest",
                        repository.string,
                    )

                    response = await self.githubapi.generic(
                        endpoint=f"/repos/{repository.data.full_name}/releases/latest",
                        etag=repository.data.etag_releases,
                    )
                    response.data = GitHubReleaseModel(
                        response.data) if response.data else None

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

                if (
                    repository.data.prerelease
                    and repository.data.prerelease == repository.data.last_version
                ):
                    repository.data.prerelease = None

            except GitHubNotModifiedException:
                repository.data.releases = True
                repository.logger.info(
                    "%s Release data is up to date",
                    repository.string,
                )
            except GitHubNotFoundException:
                repository.data.releases = False
                repository.logger.info(
                    "%s No releases found", repository.string)
            except GitHubException as exception:
                repository.data.releases = False
                repository.logger.error("%s %s", repository.string, exception)

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
                self.queue.add(self.concurrent_update_repository(
                    repository=repository))
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
    ) -> dict[str, Any]:
        """Summarize data."""
        changed = 0

        current_count = len(current_data.keys())
        new_count = len(updated_data.keys())

        for repo_id, repo_data in updated_data.items():
            if not dicts_are_equal(
                a=repo_data,
                b=current_data.get(repo_id, {}),
                ignore=COMPARE_IGNORE,
            ):
                changed += 1

        async def _rate_limit() -> dict[str, Any]:
            res = await self.async_github_api_method(
                method=self.githubapi.rate_limit,
            )
            return {
                "core": {
                    "used": res.data.resources.core.used,
                    "limit": res.data.resources.core.limit,
                    "reset": res.data.resources.core.reset,
                },
                "graphql": {
                    "used": res.data.resources.graphql.used,
                    "limit": res.data.resources.graphql.limit,
                    "reset": res.data.resources.graphql.reset,
                },
            }

        summary = {
            "changed_pct": round((changed / new_count) * 100),
            "changed": changed,
            "current_count": current_count,
            "diff": abs(new_count - current_count),
            "new_count": new_count,
            "rate_limit": await _rate_limit(),
        }

        jsonprint(summary)

        if len(updated_data) == 1:
            jsonprint(updated_data)

        return summary

    async def async_github_get_hacs_default_file(self, filename: str) -> list:
        """Get the content of a default file."""
        response = await self.async_github_api_method(
            method=self.githubapi.repos.contents.get,
            repository=HacsGitHubRepo.DEFAULT,
            path=filename,
        )
        if response is None:
            return []

        return json_loads(decode_content(response.data.content))


async def generate_category_data(category: str, repository_name: str = None):
    """Generate data."""
    async with ClientSession() as session:
        hacs = AdjustedHacs(
            session=session, token=os.getenv("DATA_GENERATOR_TOKEN"))
        os.makedirs(os.path.join(OUTPUT_DIR, category), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "diff"), exist_ok=True)
        force = os.environ.get("FORCE_REPOSITORY_UPDATE") == "True"
        stored_data = await hacs.data_client.get_data(category, validate=False)
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
            category,
            repository_name,
            current_data,
            force=force,
        )

        summary = await hacs.summarize_data(current_data, updated_data)
        with open(
            os.path.join(OUTPUT_DIR, "summary.json"),
            mode="w",
            encoding="utf-8",
        ) as data_file:
            json.dump(
                summary,
                data_file,
                cls=JSONEncoder,
                sort_keys=True,
                indent=2,
            )

        did_raise = False
        if (
            not updated_data
            or len(updated_data) == 0
            or not isinstance(updated_data, dict)
        ):
            print_error_and_exit("Updated data is empty", category)
            did_raise = True

        try:
            VALIDATE_GENERATED_V2_REPO_DATA[category](updated_data)
        except vol.Invalid as error:
            did_raise = True
            errors = expand_and_humanize_error(updated_data, error)
            if isinstance(errors, list):
                for err in errors:
                    print(f"::error::{err}")
                sys.exit(1)

            print_error_and_exit(f"Invalid data: {errors}", category)

        if did_raise:
            print_error_and_exit(
                "Validation did raise but did not exit!", category)
            sys.exit(1)  # Fallback, should not be reached

        with open(
            os.path.join(OUTPUT_DIR, category, "stored.json"),
            mode="w",
            encoding="utf-8",
        ) as data_file:
            json.dump(
                stored_data,
                data_file,
                cls=JSONEncoder,
                separators=(",", ":"),
            )
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
                {
                    i: {
                        k: v
                        for k, v in d.items() if k not in COMPARE_IGNORE
                    }
                    for i, d in current_data.items()
                },
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
                {
                    i: {
                        k: v
                        for k, v in d.items() if k not in COMPARE_IGNORE
                    }
                    for i, d in updated_data.items()
                },
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
