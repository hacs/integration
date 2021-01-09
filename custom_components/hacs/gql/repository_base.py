"""GraphQL Query to get repository base information."""
from aiogithubapi import GitHub
from ..dataclass import RepositoryInterface


async def repository_base(github: GitHub, identifier: RepositoryInterface):
    """Generate query to get repository information."""
    query = {
        "variables": {
            "owner": identifier.owner,
            "repo": identifier.repository,
        },
        "query": """
          query($owner: String!, $repo: String!) {
            repository(owner: $owner, name: $repo) {
              description
              hasIssuesEnabled
              isArchived
              isFork
              stargazerCount
              viewerHasStarred
              defaultBranchRef {
                name
              }
              pushedAt
              createdAt
              repositoryTopics(first: 100) {
                nodes {
                  topic {
                    name
                  }
                }
              }
              issues(states: OPEN, first: 100) {
                nodes {
                  number
                }
              }
              releases(last: 30) {
                nodes {
                  tagName
                  isDraft
                  isPrerelease
                  publishedAt
                  releaseAssets(first: 5) {
                    nodes {
                      downloadCount
                      name
                    }
                  }
                }
              }
              databaseId
            }
          }
          """,
    }
    data = await github.client.post(
        "/graphql",
        True,
        data=query,
        jsondata=True,
    )
    return RepositoryBaseInformation(data["data"])


class RepositoryBaseInformation:
    def __init__(self, data: dict):
        self._data = data

    @property
    def description(self):
        return self._data.get("repository", {}).get("description")

    @property
    def hasIssuesEnabled(self):
        return self._data.get("repository", {}).get("hasIssuesEnabled")

    @property
    def isArchived(self):
        return self._data.get("repository", {}).get("isArchived")

    @property
    def isFork(self):
        return self._data.get("repository", {}).get("isFork")

    @property
    def viewerHasStarred(self):
        return self._data.get("repository", {}).get("viewerHasStarred")

    @property
    def defaultBranchRef(self):
        return self._data.get("repository", {}).get("defaultBranchRef", {}).get("name")

    @property
    def pushedAt(self):
        return self._data.get("repository", {}).get("pushedAt")

    @property
    def createdAt(self):
        return self._data.get("repository", {}).get("createdAt")

    @property
    def databaseId(self):
        return str(self._data.get("repository", {}).get("databaseId"))

    @property
    def stargazerCount(self):
        return self._data.get("repository", {}).get("stargazerCount")

    @property
    def releases(self):
        return [
            release
            for release in self._data.get("repository", {})
            .get("releases", {})
            .get("nodes", [])
            if release and not release["isDraft"]
        ]

    @property
    def issues(self):
        return self._data.get("repository", {}).get("issues", {}).get("nodes", [])

    @property
    def topics(self):
        return (
            self._data.get("repository", {})
            .get("repositoryTopics", {})
            .get("nodes", [])
        )

    @property
    def has_releases(self):
        return len(self.releases) != 0
