"""GitHub GraphQL Queries."""

GET_REPOSITORY_RELEASES = """
query ($owner: String!, $name: String!, $first: Int!) {
  rateLimit {
    cost
  }
  repository(owner: $owner, name: $name) {
    releases(first: $first, orderBy: {field: CREATED_AT, direction: DESC}) {
      nodes {
        tagName
        name
        isPrerelease
        publishedAt
      }
    }
  }
}
"""
