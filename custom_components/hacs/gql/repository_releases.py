"""GraphQL Query to get repository base information."""
from aiogithubapi import GitHub
from ..dataclass import RepositoryIdentifier


async def repository_releases(
    github: GitHub, identifier: RepositoryIdentifier, pre_release: bool = False
):
    """Generate query to get repository releases."""
    query = """
          query($owner: String!, $repo: String!) {
            repository(owner: $owner, name: $repo) {
              releases(last: 30) {
                nodes {
                  name
                  tagName
                  description
                  isDraft
                  url
                  isPrerelease
                  publishedAt
                }
              }
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
    releases = [
        release
        for release in data.get("repository", {}).get("releases", {}).get("nodes", [])
        if release and not release.get("isDraft", False)
    ]
    if pre_release:
        return releases
    return [release for release in releases if not release.get("isPrerelease", False)]
