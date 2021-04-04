"""GraphQL Query to get repository base information."""
from aiogithubapi import GitHub
from ..dataclass import RepositoryIdentifier


async def repository_base(
    github: GitHub, identifier: RepositoryIdentifier, pre_release: bool = False
):
    """Generate query to get repository information."""
    query = """
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
          """
    data = await github.graphql(
        query=query,
        variables={
            "owner": identifier.owner,
            "repo": identifier.repository,
        },
    )
    return RepositoryBaseInformation(data, pre_release)


class RepositoryBaseInformation:
    def __init__(self, data: dict, pre_release: bool = False):
        self._data = data
        self._pre_release = pre_release

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
        releases = [
            release
            for release in self._data.get("repository", {})
            .get("releases", {})
            .get("nodes", [])
            if release and not release.get("isDraft", False)
        ]
        if self._pre_release:
            return releases
        return [
            release for release in releases if not release.get("isPrerelease", False)
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
