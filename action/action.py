"""Validate a GitHub repository to be used with HACS."""

from __future__ import annotations

import asyncio
import json
import logging
import os

from aiogithubapi import GitHub, GitHubAPI
import aiohttp
from homeassistant.core import HomeAssistant

from custom_components.hacs.base import HacsBase
from custom_components.hacs.const import HACS_ACTION_GITHUB_API_HEADERS
from custom_components.hacs.enums import HacsGitHubRepo
from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.utils.decode import decode_content
from custom_components.hacs.utils.logger import LOGGER
from custom_components.hacs.validate.manager import ValidationManager

TOKEN = os.getenv("INPUT_GITHUB_TOKEN")
GITHUB_WORKSPACE = os.getenv("GITHUB_WORKSPACE")
GITHUB_ACTOR = os.getenv("GITHUB_ACTOR")
GITHUB_EVENT_PATH = os.getenv("GITHUB_EVENT_PATH")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")
CHANGED_FILES = os.getenv("CHANGED_FILES", "")


REPOSITORY = os.getenv("REPOSITORY", os.getenv("INPUT_REPOSITORY"))
CATEGORY = os.getenv("CATEGORY", os.getenv("INPUT_CATEGORY", ""))


CATEGORIES = [
    "appdaemon",
    "integration",
    "plugin",
    "python_script",
    "template",
    "theme",
]


logging.basicConfig(
    format="::%(levelname)s:: %(message)s",
    level=logging.DEBUG,
)


def error(error: str):
    LOGGER.error(error)
    exit(1)


def output_in_group(group: str, content: str):
    print(f"::group::{group}")  # noqa: T201
    print(content)  # noqa: T201
    print("::endgroup::")  # noqa: T201


def get_event_data():
    if GITHUB_EVENT_PATH is None or not os.path.exists(GITHUB_EVENT_PATH):
        return {}
    with open(GITHUB_EVENT_PATH) as ev:
        return json.loads(ev.read())


async def choose_repository(githubapi: GitHubAPI, category: str):
    if category is None:
        return None

    response = await githubapi.repos.contents.get(HacsGitHubRepo.DEFAULT, category)
    current = json.loads(decode_content(response.data.content))

    with open(f"{GITHUB_WORKSPACE}/{category}") as cat_file:  # noqa: ASYNC230
        new = json.loads(cat_file.read())

    for repo in current:
        if repo in new:
            new.remove(repo)

    if len(new) != 1:
        error(f"{new} is not a single repository")

    return new[0]


def choose_category():
    for name in CHANGED_FILES.split(" "):
        if name in CATEGORIES:
            return name


async def preflight():
    """Preflight checks."""
    event_data = get_event_data()
    ref: str | None = None

    hacs = HacsBase()
    hacs.hass = HomeAssistant("")

    hacs.system.action = True
    hacs.configuration.token = TOKEN
    hacs.core.config_path = None

    async with aiohttp.ClientSession() as session:
        hacs.session = session
        hacs.validation = ValidationManager(hacs=hacs, hass=hacs.hass)
        hacs.githubapi = GitHubAPI(
            token=hacs.configuration.token,
            session=session,
            client_name="HACS/Action",
        )

        if REPOSITORY and CATEGORY:
            repository = REPOSITORY
            category = CATEGORY
        elif GITHUB_REPOSITORY == HacsGitHubRepo.DEFAULT:
            category = choose_category()
            repository = await choose_repository(hacs.githubapi, category)
            LOGGER.info(f"Actor: {GITHUB_ACTOR}")
        else:
            category = CATEGORY.lower()
            if event_data.get("pull_request") is not None:
                head = event_data["pull_request"]["head"]
                ref = head["ref"]
                repository = head["repo"]["full_name"]
            else:
                repository = GITHUB_REPOSITORY
                if event_data.get("ref") is not None:
                    # For push events
                    ref = event_data["ref"]

                    # For tag events
                    if ref.startswith("refs/tags/"):
                        ref = ref.split("/")[-1]

        LOGGER.info(f"Category: {category}")
        LOGGER.info(f"Repository: {repository}{f'@{ref}' if ref else ''}")

        if TOKEN is None:
            error("No GitHub token found, use env GITHUB_TOKEN to set this.")

        if repository is None:
            error("No repository found, use env REPOSITORY to set this.")

        if category is None:
            error("No category found, use env CATEGORY to set this.")

        if category not in CATEGORIES:
            error(f"Category {category} is not valid.")

        if ref is None and GITHUB_REPOSITORY != HacsGitHubRepo.DEFAULT:
            repo = await hacs.githubapi.repos.get(repository)
            ref = repo.data.default_branch

        await validate_repository(hacs, repository, category, ref)


async def validate_repository(hacs: HacsBase, repository: str, category: str, ref=None):
    """Validate."""
    # Legacy GitHub client
    hacs.github = GitHub(
        hacs.configuration.token,
        hacs.session,
        headers=HACS_ACTION_GITHUB_API_HEADERS,
    )

    try:
        await hacs.async_register_repository(
            repository_full_name=repository,
            category=category,
            ref=ref,
        )
    except HacsException as exception:
        error(exception)

    if (repo := hacs.repositories.get_by_full_name(repository)) is None:
        error(f"Repository {repository} not loaded properly in HACS.")

    output_in_group("data", json.dumps(repo.data.to_json(), indent=4))


if __name__ == "__main__":
    asyncio.run(preflight())
