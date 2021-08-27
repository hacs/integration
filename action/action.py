"""Validate a GitHub repository to be used with HACS."""
import asyncio
import json
import os

from aiogithubapi import GitHub
import aiohttp
from homeassistant.core import HomeAssistant

from custom_components.hacs.const import HACS_ACTION_GITHUB_API_HEADERS
from custom_components.hacs.exceptions import HacsException
from custom_components.hacs.helpers.functions.register_repository import (
    register_repository,
)
from custom_components.hacs.share import get_hacs
from custom_components.hacs.utils.logger import getLogger

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
    "netdaemon",
    "plugin",
    "python_script",
    "theme",
]

logger = getLogger()


def error(error: str):
    logger.error(error)
    exit(1)


def get_event_data():
    if GITHUB_EVENT_PATH is None or not os.path.exists(GITHUB_EVENT_PATH):
        return {}
    with open(GITHUB_EVENT_PATH) as ev:
        return json.loads(ev.read())


def chose_repository(category):
    if category is None:
        return
    with open(f"/default/{category}") as cat_file:
        current = json.loads(cat_file.read())
    with open(f"{GITHUB_WORKSPACE}/{category}") as cat_file:
        new = json.loads(cat_file.read())

    for repo in current:
        if repo in new:
            new.remove(repo)

    if len(new) != 1:
        error(f"{new} is not a single repository")

    return new[0]


def chose_category():
    for name in CHANGED_FILES.split(" "):
        if name in CATEGORIES:
            return name


async def preflight():
    """Preflight checks."""
    logger.warning("This action is deprecated. Use https://github.com/hacs/action instead")
    event_data = get_event_data()
    ref = None
    if REPOSITORY and CATEGORY:
        repository = REPOSITORY
        category = CATEGORY
        pr = False
    elif GITHUB_REPOSITORY == "hacs/default":
        category = chose_category()
        repository = chose_repository(category)
        pr = False
        logger.info(f"Actor: {GITHUB_ACTOR}")
    else:
        category = CATEGORY.lower()
        pr = True if event_data.get("pull_request") is not None else False
        if pr:
            head = event_data["pull_request"]["head"]
            ref = head["ref"]
            repository = head["repo"]["full_name"]
        else:
            repository = GITHUB_REPOSITORY

    logger.info(f"Category: {category}")
    logger.info(f"Repository: {repository}")

    if TOKEN is None:
        error("No GitHub token found, use env GITHUB_TOKEN to set this.")

    if repository is None:
        error("No repository found, use env REPOSITORY to set this.")

    if category is None:
        error("No category found, use env CATEGORY to set this.")

    async with aiohttp.ClientSession() as session:

        github = GitHub(TOKEN, session, headers=HACS_ACTION_GITHUB_API_HEADERS)
        repo = await github.get_repo(repository)
        if not pr and repo.description is None:
            error("Repository is missing description")
        if not pr and not repo.attributes["has_issues"]:
            error("Repository does not have issues enabled")
        if ref is None and GITHUB_REPOSITORY != "hacs/default":
            ref = repo.default_branch

    await validate_repository(repository, category, ref)


async def validate_repository(repository, category, ref=None):
    """Validate."""
    async with aiohttp.ClientSession() as session:
        hacs = get_hacs()
        hacs.hass = HomeAssistant()
        hacs.session = session
        hacs.configuration.token = TOKEN
        hacs.core.config_path = None
        hacs.github = GitHub(
            hacs.configuration.token,
            hacs.session,
            headers=HACS_ACTION_GITHUB_API_HEADERS,
        )
        try:
            await register_repository(repository, category, ref=ref)
        except HacsException as exception:
            error(exception)


LOOP = asyncio.get_event_loop()
LOOP.run_until_complete(preflight())
