"""Validate a GitHub repository to be used with HACS."""
import sys
import os
import asyncio
import logging
import aiohttp
import json
from aiogithubapi import AIOGitHub, AIOGitHubException
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from custom_components.hacs.globals import get_hacs
from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.helpers.register_repository import register_repository

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

FORMATTER = logging.Formatter("%(name)s - %(message)s")

HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setLevel(logging.DEBUG)
HANDLER.setFormatter(FORMATTER)

LOGGER.addHandler(HANDLER)

TOKEN = os.getenv("ACTIONS_RUNTIME_TOKEN")
GITHUB_WORKSPACE = os.getenv("GITHUB_WORKSPACE")

def chose_repository(category):
    if category is None:
        return
    with open(f"/default/{category}", "r") as cat_file:
        current = json.loads(cat_file.read())
    with open(f"{GITHUB_WORKSPACE}/{category}", "r") as cat_file:
        new = json.loads(cat_file.read())

    for repo in current:
        new.remove(repo)
    
    if len(new) != 1:
        print(f"{new} is not a single repo")

    return new[0]

def chose_category():
    for name in os.getenv("CHANGED_FILES", "").split(" "):
        if name in ["plugin", "integration"]:
            return name

async def preflight():
    """Preflight cheks."""
    category = os.getenv("INPUT_CATEGORY") or chose_category()
    repository = os.getenv("INPUT_REPOSITORY") or chose_repository(category)

    print(f"Category: {category}")
    print(f"Repository: {repository}")

    if TOKEN is None:
        print("No GitHub token found, use env GITHUB_TOKEN to set this.")
        exit(1)

    if repository is None:
        print("No repository found, use env REPOSITORY to set this.")
        exit(1)

    if category is None:
        print("No category found, use env CATEGORY to set this.")
        exit(1)

    async with aiohttp.ClientSession() as session:
        github = AIOGitHub(TOKEN, session)
        repo = await github.get_repo(repository)
        if repo.description is None:
            print("Repository is missing description")
            exit(1)
        if not repo.attributes["has_issues"]:
            print("Repository does not have issues enabled")
            exit(1)

    await validate_repository(repository, category)


async def validate_repository(repository, category):
    """Validate."""
    async with aiohttp.ClientSession() as session:
        hacs = get_hacs()
        hacs.session = session
        hacs.configuration = Configuration()
        hacs.configuration.token = TOKEN
        hacs.github = AIOGitHub(hacs.configuration.token, hacs.session)
        await register_repository(repository, category)
        print("All good!")



LOOP = asyncio.get_event_loop()
LOOP.run_until_complete(preflight())