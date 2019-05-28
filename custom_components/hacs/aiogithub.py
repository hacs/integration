"""Async Github API implementation."""
import async_timeout

class AIOGitHubBaseException(BaseException):
    """Raise this when something is off."""

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
        self.headers["Authorization"] = "token {}".format(token)

    async def get_repo(self, repo: str):
        """Retrun AIOGithubRepository object."""
        endpoint = "/repos/" + repo
        url = self.baseapi + endpoint

        async with async_timeout.timeout(10, loop=self.loop):
            response = await self.session.get(url, headers=self.headers)
            response = await response.json()

            if response.get("message"):
                raise AIOGitHubBaseException(response["message"])

            return AIOGithubRepository(response, self.token, self.loop, self.session)


class AIOGithubRepository(AIOGitHub):
    """Repository Github API implementation."""

    def __init__(self, attributes, token, loop, session):
        """Initialize."""
        super().__init__(token, loop, session)
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


    async def get_topics(self):
        """Retrun topics."""
        endpoint = "/repos/" + self.full_name + "/topics"
        url = self.baseapi + endpoint

        headers = self.headers
        headers["Accept"] = "application/vnd.github.mercy-preview+json"

        async with async_timeout.timeout(10, loop=self.loop):
            response = await self.session.get(url, headers=headers)
            response = await response.json()

            if response.get("names"):
                return response["names"]

            elif response.get("message"):
                raise AIOGitHubBaseException(response["message"])

            return
