"""Async Github API implementation."""
import async_timeout


class AIOGitHub(object):
    """Base Github API implementation."""

    baseapi = "https://api.github.com"
    headers = {
        "Accept": "application/vnd.github.v3.raw+json",
        "User-Agent": "python/AIOGitHub",
    }

    def __init__(self, token, loop, session):
        """Initialize."""
        self.headers["Authorization"] = "token {}".format(token)
        self.loop = loop
        self.session = session

    async def get_repo(self, repo: str):
        """Retrun AIOGithubRepository object."""
        endpoint = "/repos/" + repo
        url = self.baseapi + endpoint

        async with async_timeout.timeout(10, loop=self.loop):
            response = await self.session.get(url, headers=self.headers)
            response = await response.json()

        return AIOGithubRepository(response)


class AIOGithubRepository(AIOGitHub):
    """Repository Github API implementation."""

    def __init__(self, attributes):
        """Initialize."""
        super().__init__()
        self.attributes = attributes


    @property
    def id(self):
        """Repository ID."""
        return self.attributes.get("id")

    @property
    def full_name(self):
        """Repository Full name."""
        return self.attributes.get("full_name")

    @property
    def pushed_at(self):
        """pushed_at time."""
        return self.attributes.get("pushed_at")

    @property
    def archived(self):
        """archived."""
        return self.attributes.get("archived")

    @property
    def description(self):
        """description."""
        return self.attributes.get("description")
