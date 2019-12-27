import re
import sys
import json
from github import Github

BODY = """
[![Downloads for this release](https://img.shields.io/github/downloads/hacs/integration/{version}/total.svg)](https://github.com/hacs/integration/releases/{version})

{changes}

## Links

- [Discord server for HACS](https://discord.gg/apgchf8)
- [HACS Documentation](https://hacs.xyz/)
- [How to submit bugs/feature requests](https://hacs.xyz/docs/issues)
- [If you like what I (@ludeeus) do please consider sposoring me on GitHub](https://github.com/sponsors/ludeeus)
- [Or by me a ☕️ / 🍺](https://www.buymeacoffee.com/ludeeus)
"""

CHANGES = """
## Integration changes

{integration_changes}

## Frontend changes

{frontend_changes}
"""

COMMANDS = """
***
<details>
  <summary>HACS Bot commands</summary>

_Commands can only be issued by a user with write privileges to the repository._

Command | Description
-- | --
`@hacs-bot no` | Will close the issue, and not publish a new release.
`@hacs-bot close` | Same as `@hacs-bot no`.
`@hacs-bot yes` | Will create a new release and close the issue.
`@hacs-bot LGTM` | Same as `@hacs-bot yes`.
`@hacs-bot release x.xx.x` | Same as `@hacs-bot yes` but will change the release number to the one specified.

</details>
"""

CHANGE = "- [{line}]({link}) @{author}\n"
NOCHANGE = "_No changes in this release._"

GITHUB = Github(sys.argv[2])


def new_commits(repo, sha):
    """Get new commits in repo."""
    from datetime import datetime

    dateformat = "%a, %d %b %Y %H:%M:%S GMT"
    release_commit = repo.get_commit(sha)
    since = datetime.strptime(release_commit.last_modified, dateformat)
    commits = repo.get_commits(since=since)
    if len(list(commits)) == 1:
        return False
    return reversed(list(commits)[:-1])


def last_integration_release(github, skip=True):
    """Return last release."""
    repo = github.get_repo("hacs/integration")
    tag_sha = None
    data = {}
    tags = list(repo.get_tags())
    reg = "(v|^)?(\\d+\\.)?(\\d+\\.)?(\\*|\\d+)$"
    if tags:
        for tag in tags:
            tag_name = tag.name
            if re.match(reg, tag_name):
                tag_sha = tag.commit.sha
                if skip:
                    skip = False
                    continue
                break
    data["tag_name"] = tag_name
    data["tag_sha"] = tag_sha
    return data


def last_frontend_release(repo, tag_name):
    """Return last release."""
    tags = list(repo.get_tags())
    if tags:
        for tag in tags:
            if tag_name == tag.name:
                return tag.commit.sha


def get_frontend_commits(github, skip=True):
    changes = ""
    repo = github.get_repo("hacs/frontend")
    integration = github.get_repo("hacs/integration")
    last_tag = last_integration_release(github, skip)["tag_name"]
    contents = integration.get_contents(
        "custom_components/hacs/manifest.json", ref=f"refs/tags/{last_tag}"
    )
    for req in json.loads(contents.decoded_content)["requirements"]:
        if "hacs_frontend" in req:
            hacs_frontend = req.split("=")[1]
    commits = new_commits(repo, last_frontend_release(repo, hacs_frontend))

    if not commits:
        changes = NOCHANGE
    else:
        for commit in commits:
            msg = repo.get_git_commit(commit.sha).message
            if "\n" in msg:
                msg = msg.split("\n")[0]
            changes += CHANGE.format(
                line=msg, link=commit.html_url, author=commit.author.login
            )

    return changes


def get_integration_commits(github, skip=True):
    changes = ""
    repo = github.get_repo("hacs/integration")
    commits = new_commits(repo, last_integration_release(github, skip)["tag_sha"])

    if not commits:
        changes = NOCHANGE
    else:
        for commit in commits:
            msg = repo.get_git_commit(commit.sha).message
            if "\n" in msg:
                msg = msg.split("\n")[0]
            changes += CHANGE.format(
                line=msg, link=commit.html_url, author=commit.author.login
            )

    return changes


## Update release notes:
UPDATERELEASE = str(sys.argv[4])
REPO = GITHUB.get_repo("hacs/integration")
if UPDATERELEASE == "yes":
    VERSION = str(sys.argv[6]).replace("refs/tags/", "")
    RELEASE = REPO.get_release(VERSION)
    RELEASE.update_release(
        name=VERSION,
        message=BODY.format(
            version=VERSION,
            changes=CHANGES.format(
                integration_changes=get_integration_commits(GITHUB),
                frontend_changes=get_frontend_commits(GITHUB),
            ),
        ),
    )
else:
    frontend_changes = get_frontend_commits(GITHUB, False)
    integration_changes = get_integration_commits(GITHUB, False)
    if integration_changes != NOCHANGE or frontend_changes != NOCHANGE:
        VERSION = last_integration_release(GITHUB, False)["tag_name"]
        VERSION = f"{VERSION[:-1]}{int(VERSION[-1])+1}"
        REPO.create_issue(
            title=f"Create release {VERSION}?",
            labels=["New release"],
            assignee="ludeeus",
            body=CHANGES.format(
                integration_changes=integration_changes,
                frontend_changes=frontend_changes,
            )
            + COMMANDS,
        )
    else:
        print("Not enough changes for a release.")
