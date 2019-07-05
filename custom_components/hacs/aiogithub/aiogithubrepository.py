"""AioGitHub: Repository"""
from asyncio import CancelledError, TimeoutError
from datetime import datetime

import async_timeout
import backoff
from aiohttp import ClientError

from .aiogithub import AIOGitHub
from .aiogithubrepositorycontent import AIOGithubRepositoryContent
from .aiogithubrepositoryrelease import AIOGithubRepositoryRelease
from .const import BASE_URL
from .exceptions import AIOGitHubException, AIOGitHubRatelimit


class AIOGithubRepository(AIOGitHub):
    """Repository Github API implementation."""

    def __init__(self, attributes, token, loop, session):
        """Initialize."""
        super().__init__(token, loop, session)
        self.attributes = attributes
        self._last_commit = None

    @property
    def id(self):
        return self.attributes.get("id")

    @property
    def full_name(self):
        return self.attributes.get("full_name")

    @property
    def pushed_at(self):
        return datetime.strptime(self.attributes.get("pushed_at"), "%Y-%m-%dT%H:%M:%SZ")

    @property
    def archived(self):
        return self.attributes.get("archived")

    @property
    def description(self):
        return self.attributes.get("description")

    @property
    def topics(self):
        return self.attributes.get("topics")

    @property
    def default_branch(self):
        return self.attributes.get("default_branch")

    @property
    def last_commit(self):
        return self._last_commit

    @backoff.on_exception(
        backoff.expo, (ClientError, CancelledError, TimeoutError, KeyError), max_tries=5
    )
    async def get_contents(self, path, ref=None):
        """Retrun a list of repository content objects."""
        if self.ratelimit_remaining == "0":
            raise AIOGitHubRatelimit("GitHub Ratelimit error")
        endpoint = "/repos/" + self.full_name + "/contents/" + path
        url = BASE_URL + endpoint

        params = {"path": path}
        if ref is not None:
            params["ref"] = ref.replace("tags/", "")

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.get(url, headers=self.headers, params=params)
            self.ratelimit_remaining = response.headers.get("x-ratelimit-remaining")
            response = await response.json()

            if self.ratelimit_remaining == "0":
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if not isinstance(response, list):
                if response.get("message"):
                    if response.get("message") == "Not Found":
                        raise AIOGitHubException(
                            "{} does not exist in the repository.".format(path)
                        )
                    else:
                        raise AIOGitHubException(response["message"])
                return AIOGithubRepositoryContent(response)

            contents = []

            for content in response:
                contents.append(AIOGithubRepositoryContent(content))

        return contents

    @backoff.on_exception(
        backoff.expo, (ClientError, CancelledError, TimeoutError, KeyError), max_tries=5
    )
    async def get_releases(self, prerelease=False):
        """Retrun a list of repository release objects."""
        if self.ratelimit_remaining == "0":
            raise AIOGitHubRatelimit("GitHub Ratelimit error")
        endpoint = "/repos/{}/releases".format(self.full_name)
        url = BASE_URL + endpoint

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.get(url, headers=self.headers)
            self.ratelimit_remaining = response.headers.get("x-ratelimit-remaining")
            response = await response.json()

            if self.ratelimit_remaining == "0":
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if not isinstance(response, list):
                if response.get("message"):
                    return False

            contents = []

            for content in response:
                if len(contents) == 5:
                    break
                if not prerelease:
                    if content.get("prerelease", False):
                        continue
                contents.append(AIOGithubRepositoryRelease(content))

        return contents

    @backoff.on_exception(
        backoff.expo, (ClientError, CancelledError, TimeoutError, KeyError), max_tries=5
    )
    async def set_last_commit(self):
        """Retrun a list of repository release objects."""
        if self.ratelimit_remaining == "0":
            raise AIOGitHubRatelimit("GitHub Ratelimit error")
        endpoint = "/repos/" + self.full_name + "/commits/" + self.default_branch
        url = BASE_URL + endpoint

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.get(url, headers=self.headers)
            self.ratelimit_remaining = response.headers.get("x-ratelimit-remaining")
            response = await response.json()

            if self.ratelimit_remaining == "0":
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if response.get("message"):
                raise AIOGitHubException("No commits")

        self._last_commit = response["sha"][0:7]
