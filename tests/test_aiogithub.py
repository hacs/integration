"""Tests for AIOGitHub."""

import json

import aiohttp
import pytest

from custom_components.hacs.aiogithub import AIOGitHub
from custom_components.hacs.aiogithub.aiogithubrepository import AIOGithubRepository
from .data.aiogithub import response_get_repo_awesome

TOKEN = "xxx"
HEADERS = {"Content-Type": "application/json"}


@pytest.mark.asyncio
async def test_get_repo_awesome(aresponses, event_loop, response_get_repo_awesome):
    """Test AIOGitHub.get_repo("awesome-dev/awesome-repo")."""
    aresponses.add(
        "api.github.com",
        "/repos/awesome-dev/awesome-repo",
        "GET",
        aresponses.Response(
            text=json.dumps(response_get_repo_awesome), status=200, headers=HEADERS
        ),
    )

    async with aiohttp.ClientSession(loop=event_loop) as session:
        github = AIOGitHub(TOKEN, event_loop, session)
        repository = await github.get_repo("awesome-dev/awesome-repo")
        assert isinstance(repository, AIOGithubRepository)
        assert repository.id == 99999999
