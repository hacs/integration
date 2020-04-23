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
        print(f"{new} is not a single repo")
        exit(1)

    return new[0]

def chose_category():
    for name in os.getenv("CHANGED_FILES", "").split(" "):
        if name in CATEGORIES:
            return name

async def preflight():
    """Preflight cheks."""
    ref = os.getenv("GITHUB_HEAD_REF") 
    if os.getenv("GITHUB_REPOSITORY") == "hacs/default":
        categoty = chose_category()
        repository = chose_repository(category)
        ref = None
        print(f"Actor: {GITHUB_ACTOR}")
    else:
        category = os.getenv("INPUT_CATEGORY")
        event_data = get_event_data()
        pr = True if event_data.get("pull_request") is not None else False
        if not pr:
            repository = os.getenv("GITHUB_REPOSITORY")
        else:
            head = event_data["pull_request"]["head"]
            ref = head["ref"]
            repository = head["repo"]["full_name"]

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
        if not pr and repo.description is None:
            print("Repository is missing description")
            exit(1)
        if not pr and not repo.attributes["has_issues"]:
            print("Repository does not have issues enabled")
            exit(1)

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
        except HacsException:
            exit(1)
        print("All good!")



LOOP = asyncio.get_event_loop()
LOOP.run_until_complete(preflight())