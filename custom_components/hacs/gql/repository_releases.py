"""GraphQL Query to get repository base information."""
from aiogithubapi import GitHub
from ..dataclass import RepositoryInterface


async def repository_releases(github: GitHub, identifier: RepositoryInterface):
    """Generate query to get repository releases."""
    query = {
        "variables": {
            "owner": identifier.owner,
            "repo": identifier.repository,
        },
        "query": """
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
          """,
    }
    data = await github.client.post(
        "/graphql",
        True,
        data=query,
        jsondata=True,
    )
    return [
        release
        for release in data.get("data", {})
        .get("repository", {})
        .get("releases", {})
        .get("nodes", [])
        if release and not release["isDraft"]
    ]
