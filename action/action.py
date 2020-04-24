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
from custom_components.hacs.hacsbase.exceptions import HacsException
from custom_components.hacs.hacsbase.configuration import Configuration
from custom_components.hacs.helpers.register_repository import register_repository

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

FORMATTER = logging.Formatter("%(name)s - %(message)s")

HANDLER = logging.StreamHandler(sys.stdout)
HANDLER.setLevel(logging.DEBUG)
HANDLER.setFormatter(FORMATTER)

LOGGER.addHandler(HANDLER)

TOKEN = os.getenv("INPUT_GITHUB_TOKEN")
GITHUB_WORKSPACE = os.getenv("GITHUB_WORKSPACE")
GITHUB_ACTOR = os.getenv("GITHUB_ACTOR")

CATEGORIES = [
    "appdaemon",
    "integration",
    "netdaemon",
    "plugin",
    "python_script",
    "theme"
]

def get_event_data():
    if os.getenv("GITHUB_EVENT_PATH") is None:
        return {}
    with open(os.getenv("GITHUB_EVENT_PATH"), "r") as ev:
        return json.loads(ev.read())

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
        exit(f"{new} is not a single repo")

    return new[0]

def chose_category():
    for name in os.getenv("CHANGED_FILES", "").split(" "):
        if name in CATEGORIES:
            return name

async def preflight():
    """Preflight cheks."""
    event_data = get_event_data()
    if os.getenv("GITHUB_REPOSITORY") == "hacs/default":
        category = chose_category()
        repository = chose_repository(category)
        ref = None
        pr = False
        print(f"Actor: {GITHUB_ACTOR}")
    else:
        category = os.getenv("INPUT_CATEGORY").lower()
        pr = True if event_data.get("pull_request") is not None else False
        if pr:
            head = event_data["pull_request"]["head"]
            ref = head["ref"]
            repository = head["repo"]["full_name"]
        else:
            repository = os.getenv("GITHUB_REPOSITORY")
            ref = os.getenv("GITHUB_HEAD_REF")

    print(f"Category: {category}")
    print(f"Repository: {repository}")

    if TOKEN is None:
        exit("No GitHub token found, use env GITHUB_TOKEN to set this.")

    if repository is None:
        exit("No repository found, use env REPOSITORY to set this.")

    if category is None:
        exit("No category found, use env CATEGORY to set this.")

    async with aiohttp.ClientSession() as session:
        github = AIOGitHub(TOKEN, session)
        repo = await github.get_repo(repository)
        if not pr and repo.description is None:
            exit("Repository is missing description")
        #if not pr and not repo.attributes["has_issues"]:
            #exit("Repository does not have issues enabled")

    await validate_repository(repository, category, ref)


async def validate_repository(repository, category, ref=None):
    """Validate."""
    async with aiohttp.ClientSession() as session:
        hacs = get_hacs()
        hacs.session = session
        hacs.configuration = Configuration()
        hacs.configuration.token = TOKEN
        hacs.github = AIOGitHub(hacs.configuration.token, hacs.session)
        try:
            await register_repository(repository, category, ref=ref, action=True)
        except HacsException as exception:
            exit(exception)
        print("All good!")



LOOP = asyncio.get_event_loop()
LOOP.run_until_complete(preflight())