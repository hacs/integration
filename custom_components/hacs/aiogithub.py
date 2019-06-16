"""Async Github API implementation."""
# pylint: disable=super-init-not-called,missing-docstring,invalid-name
import base64
import logging
from datetime import datetime

import async_timeout
from aiohttp import ClientError

import backoff

_LOGGER = logging.getLogger("custom_components.hacs.aiogithub")


class AIOGitHubException(BaseException):
    """Raise this when something is off."""


class AIOGitHubRatelimit(AIOGitHubException):
    """Raise this when we hit the ratelimit."""


class AIOGitHub(object):
    """Base Github API implementation."""

    baseapi = "https://api.github.com"
    headers = {
        "Accept": "application/vnd.github.v3.raw+json",
        "User-Agent": "python/AIOGitHub",
    }

    def __init__(self, token, loop, session):
        """Must be called before anything else."""
        self.token = token
        self.loop = loop
        self.session = session
        self._ratelimit_remaining = None
        self.headers["Authorization"] = "token {}".format(token)

    @backoff.on_exception(backoff.expo, ClientError, max_tries=3)
    async def get_repo(self, repo: str):
        """Retrun AIOGithubRepository object."""
        if self._ratelimit_remaining == 0:
            raise AIOGitHubRatelimit("GitHub Ratelimit error")

        endpoint = "/repos/" + repo
        url = self.baseapi + endpoint

        headers = self.headers
        headers["Accept"] = "application/vnd.github.mercy-preview+json"

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.get(url, headers=headers)
            self._ratelimit_remaining = response.headers["x-ratelimit-remaining"]
            response = await response.json()

            if self._ratelimit_remaining == 0:
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if response.get("message"):
                raise AIOGitHubException(response["message"])

        return AIOGithubRepository(response, self.token, self.loop, self.session)

    @backoff.on_exception(backoff.expo, ClientError, max_tries=3)
    async def get_org_repos(self, org: str, page=1):
        """Retrun a list of AIOGithubRepository objects."""
        if self._ratelimit_remaining == 0:
            raise AIOGitHubRatelimit("GitHub Ratelimit error")
        endpoint = "/orgs/" + org + "/repos?page=" + str(page)
        url = self.baseapi + endpoint

        params = {"per_page": 100}

        headers = self.headers
        headers["Accept"] = "application/vnd.github.mercy-preview+json"

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.get(url, headers=headers, params=params)
            self._ratelimit_remaining = response.headers["x-ratelimit-remaining"]
            response = await response.json()

            if self._ratelimit_remaining == 0:
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if not isinstance(response, list):
                raise AIOGitHubException(response["message"])

            repositories = []

            for repository in response:
                repositories.append(
                    AIOGithubRepository(repository, self.token, self.loop, self.session)
                )

        return repositories

    @backoff.on_exception(backoff.expo, ClientError, max_tries=3)
    async def render_markdown(self, content: str):
        """Retrun AIOGithubRepository object."""
        if self._ratelimit_remaining == 0:
            raise AIOGitHubRatelimit("GitHub Ratelimit error")
        endpoint = "/markdown/raw"
        url = self.baseapi + endpoint

        headers = self.headers
        headers["Content-Type"] = "text/plain"

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.post(url, headers=headers, data=content)
            self._ratelimit_remaining = response.headers["x-ratelimit-remaining"]
            response = await response.text()

            if self._ratelimit_remaining == 0:
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if isinstance(response, dict):
                if response.get("message"):
                    raise AIOGitHubException(response["message"])

        return response

    @property
    def ratelimit_remaining(self):
        """Return the remaining calls for ratelimit."""
        return self._ratelimit_remaining


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

    @backoff.on_exception(backoff.expo, ClientError, max_tries=3)
    async def get_contents(self, path, ref=None):
        """Retrun a list of repository content objects."""
        if self._ratelimit_remaining == 0:
            raise AIOGitHubRatelimit("GitHub Ratelimit error")
        endpoint = "/repos/" + self.full_name + "/contents/" + path
        url = self.baseapi + endpoint

        params = {"path": path}
        if ref is not None:
            params["ref"] = ref

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.get(url, headers=self.headers, params=params)
            self._ratelimit_remaining = response.headers["x-ratelimit-remaining"]
            response = await response.json()

            if self._ratelimit_remaining == 0:
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

    @backoff.on_exception(backoff.expo, ClientError, max_tries=3)
    async def get_releases(self, latest=False):
        """Retrun a list of repository release objects."""
        if self._ratelimit_remaining == 0:
            raise AIOGitHubRatelimit("GitHub Ratelimit error")
        endpoint = (
            "/repos/" + self.full_name + "/releases/" + "latest" if latest else ""
        )
        url = self.baseapi + endpoint

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.get(url, headers=self.headers)
            self._ratelimit_remaining = response.headers["x-ratelimit-remaining"]
            response = await response.json()

            if self._ratelimit_remaining == 0:
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if response.get("message"):
                return False

            if latest:
                return AIOGithubRepositoryRelease(response)

            contents = []

            for content in response:
                contents.append(AIOGithubRepositoryRelease(content))

        return contents

    @backoff.on_exception(backoff.expo, ClientError, max_tries=3)
    async def set_last_commit(self):
        """Retrun a list of repository release objects."""
        if self._ratelimit_remaining == 0:
            raise AIOGitHubRatelimit("GitHub Ratelimit error")
        endpoint = "/repos/" + self.full_name + "/commits/" + self.default_branch
        url = self.baseapi + endpoint

        async with async_timeout.timeout(20, loop=self.loop):
            response = await self.session.get(url, headers=self.headers)
            self._ratelimit_remaining = response.headers["x-ratelimit-remaining"]
            response = await response.json()

            if self._ratelimit_remaining == 0:
                raise AIOGitHubRatelimit("GitHub Ratelimit error")

            if response.get("message"):
                raise AIOGitHubException("No commits")

        self._last_commit = response["sha"][0:7]


class AIOGithubRepositoryContent(AIOGitHub):
    """Repository Conetent Github API implementation."""

    def __init__(self, attributes):
        """Initialize."""
        self.attributes = attributes

    @property
    def type(self):
        return self.attributes.get("type", "file")

    @property
    def encoding(self):
        return self.attributes.get("encoding")

    @property
    def name(self):
        return self.attributes.get("name")

    @property
    def path(self):
        return self.attributes.get("path")

    @property
    def content(self):
        return base64.b64decode(
            bytearray(self.attributes.get("content"), "utf-8")
        ).decode()

    @property
    def download_url(self):
        return self.attributes.get("download_url") or self.attributes.get(
            "browser_download_url"
        )


class AIOGithubRepositoryRelease(AIOGitHub):
    """Repository Release Github API implementation."""

    def __init__(self, attributes):
        """Initialize."""
        self.attributes = attributes

    @property
    def tag_name(self):
        return self.attributes.get("tag_name")

    @property
    def name(self):
        return self.attributes.get("name")

    @property
    def published_at(self):
        return datetime.strptime(
            self.attributes.get("published_at"), "%Y-%m-%dT%H:%M:%SZ"
        )

    @property
    def draft(self):
        return self.attributes.get("draft")

    @property
    def prerelease(self):
        return self.attributes.get("prerelease")

    @property
    def assets(self):
        assetlist = []
        for item in self.attributes.get("assets"):
            assetlist.append(AIOGithubRepositoryContent(item))
        return assetlist
