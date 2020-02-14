"""Helpers to get default repositories."""
import json
from aiogithubapi import AIOGitHub, AIOGitHubException
from integrationhelper import Logger
from custom_components.hacs.helpers.information import get_repository


async def get_default_repos_orgs(github: type(AIOGitHub), category: str) -> dict:
    """Gets default org repositories."""
    repositories = []
    logger = Logger("hacs")
    orgs = {
        "plugin": "custom-cards",
        "integration": "custom-components",
        "theme": "home-assistant-community-themes",
    }
    if category not in orgs:
        return repositories

    try:
        repos = await github.get_org_repos(orgs[category])
        for repo in repos:
            repositories.append(repo.full_name)

    except AIOGitHubException as exception:
        logger.error(exception)

    return repositories


async def get_default_repos_lists(session, token, default: str) -> dict:
    """Gets repositories from default list."""
    repositories = []
    logger = Logger("hacs")

    try:
        repo = await get_repository(session, token, "hacs/default")
        content = await repo.get_contents(default)
        repositories = json.loads(content.content)

    except AIOGitHubException as exception:
        logger.error(exception)

    return repositories
