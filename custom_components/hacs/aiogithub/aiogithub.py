"""AioGitHub: Base"""
# pylint: disable=super-init-not-called,missing-docstring,invalid-name,redefined-builtin
import logging
from asyncio import CancelledError, TimeoutError

import async_timeout
from aiohttp import ClientError

import backoff

from .const import BASE_HEADERS, BASE_URL
from .exceptions import AIOGitHubAuthentication, AIOGitHubException, AIOGitHubRatelimit

_LOGGER = logging.getLogger("AioGitHub")


class AIOGitHub(object):
    """Base Github API implementation."""

    def __init__(self, token, loop, session):
        """Must be called before anything else."""
        self.token = token
        self.loop = loop
        self.session = session
        self.ratelimit_remaining = None
        self.headers = BASE_HEADERS
        self.headers["Authorization"] = "token {}".format(token)

    @backoff.on_exception(
        backoff.expo, (ClientError, CancelledError, TimeoutError, KeyError), max_tries=5
    )
    async def get_repo(self, repo: str):
        """Retrun AIOGithubRepository object."""
        from .aiogithubrepository import AIOGithubRepository
        if self.ratelimit_remaining == "0":
            raise AIOGitHubRatelimit("GitHub Ratelimit error")

        endpoint = "/repos/" + repo
        url = BASE_URL + endpoint

        headers = self.headers
        headers["Accept"] = "application/vnd.github.mercy-preview+json"

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.get(url, headers=headers)
            self.ratelimit_remaining = response.headers.get("x-ratelimit-remaining")
            response = await response.json()

            if self.ratelimit_remaining == "0":
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if response.get("message"):
                if response["message"] == "Bad credentials":
                    raise AIOGitHubAuthentication("Access token is not valid!")
                else:
                    raise AIOGitHubException(response["message"])

        return AIOGithubRepository(response, self.token, self.loop, self.session)

    @backoff.on_exception(
        backoff.expo, (ClientError, CancelledError, TimeoutError, KeyError), max_tries=5
    )
    async def get_org_repos(self, org: str, page=1):
        """Retrun a list of AIOGithubRepository objects."""
        from .aiogithubrepository import AIOGithubRepository
        if self.ratelimit_remaining == "0":
            raise AIOGitHubRatelimit("GitHub Ratelimit error")
        endpoint = "/orgs/" + org + "/repos?page=" + str(page)
        url = BASE_URL + endpoint

        params = {"per_page": 100}

        headers = self.headers
        headers["Accept"] = "application/vnd.github.mercy-preview+json"

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.get(url, headers=headers, params=params)
            self.ratelimit_remaining = response.headers.get("x-ratelimit-remaining")
            response = await response.json()

            if self.ratelimit_remaining == "0":
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if not isinstance(response, list):
                if response["message"] == "Bad credentials":
                    raise AIOGitHubAuthentication("Access token is not valid!")
                else:
                    raise AIOGitHubException(response["message"])

            repositories = []

            for repository in response:
                repositories.append(
                    AIOGithubRepository(repository, self.token, self.loop, self.session)
                )

        return repositories

    @backoff.on_exception(
        backoff.expo, (ClientError, CancelledError, TimeoutError, KeyError), max_tries=5
    )
    async def render_markdown(self, content: str):
        """Retrun AIOGithubRepository object."""
        if self.ratelimit_remaining == "0":
            raise AIOGitHubRatelimit("GitHub Ratelimit error")
        endpoint = "/markdown/raw"
        url = BASE_URL + endpoint

        headers = self.headers
        headers["Content-Type"] = "text/plain"

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.post(url, headers=headers, data=content)
            self.ratelimit_remaining = response.headers.get("x-ratelimit-remaining")
            response = await response.text()

            if self.ratelimit_remaining == "0":
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if isinstance(response, dict):
                if response.get("message"):
                    if response["message"] == "Bad credentials":
                        raise AIOGitHubAuthentication("Access token is not valid!")
                    else:
                        raise AIOGitHubException(response["message"])

        return response
