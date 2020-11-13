"""GraphQL Query to get repository information."""


def gql_query_repository_information(**kwargs):
    """Generate query to get repository information."""
    query = {
        "variables": {
            "owner": kwargs.get("owner"),
            "name": kwargs.get("name"),
        },
        "query": """
          query($owner: String!, $name: String!) {
            repository(owner: $owner, name: $name) {
              description
              hasIssuesEnabled
              isArchived
              isFork
              updatedAt
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
              releases(last: 15) {
                nodes {
                  name
                  tagName
                  description
                  releaseAssets(first: 15) {
                    nodes {
                      downloadCount
                      downloadUrl
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
    return query
