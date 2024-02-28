"""Tests for the HACS action."""
import base64
import json
import os
from unittest import mock

import pytest

from tests.common import TOKEN, MockedResponse, ResponseMocker
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "key,repository,manifest",
    [("bad_issue_tracker", "hacs-test-org/integration-basic", {"issue_tracker": None})],
)
async def test_hacs_action_integration(
    key: str,
    repository: str,
    manifest: dict[str, str | bool | None],
    caplog: pytest.LogCaptureFixture,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
):
    """Test the action."""
    basemanifest = {
        "domain": "example",
        "version": "1.0.0",
        "documentation": "https://example.com",
        "codeowners": ["hacs-test-org"],
        "issue_tracker": "https://example.com",
        "name": "Example",
    }
    envpatch = {"INPUT_GITHUB_TOKEN": TOKEN, "REPOSITORY": repository, "CATEGORY": "integration"}

    response_mocker.add(
        "https://brands.home-assistant.io/domains.json",
        response=MockedResponse(status=200, content={"custom": ["example"]}),
    )
    response_mocker.add(
        f"https://api.github.com/repos/hacs-test-org/integration-basic/contents/custom_components/example/manifest.json",
        response=MockedResponse(
            status=200,
            content={
                "content": base64.b64encode(
                    json.dumps({**basemanifest, **manifest}).encode("ascii")
                ).decode("ascii")
            },
            keep=True,
        ),
    )

    with mock.patch.dict(os.environ, envpatch), mock.patch("builtins.exit", mock.MagicMock()):
        from action.action import preflight

        await preflight()

    splitlines = [f"<{l.rsplit(' <')[1]}" for l in caplog.text.split("\n") if " <" in l]

    snapshots.assert_match(
        "\n".join(splitlines[0:2] + sorted(splitlines[2:-3]) + splitlines[-3:]),
        f"action/integration/{key}.log",
    )
