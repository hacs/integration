"""Tests for the HACS action."""
import json
import os
from unittest import mock

import pytest

from tests.common import TOKEN, MockedResponse, ResponseMocker, current_function_name
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "test_case",
    [
        pytest.param(
            {
                "manifest": {"documentation": None},
                "succeed": False,
                "releases": None,
            },
            id="bad_documentation"
        ),
        pytest.param(
            {
                "manifest": {"issue_tracker": None},
                "succeed": False,
                "releases": None,
            },
            id="bad_issue_tracker"
        ),
        pytest.param(
            {
                "manifest": {},
                "succeed": True,
                "releases": None,
            },
            id="valid_manifest"
        ),
        pytest.param(
            {
                "manifest": {},
                "succeed": True,
                "releases": [
                    {
                        "tag_name": "v1.0.0",
                        "assets": []
                    }
                ],
            },
            id="releases_without_assets"
        ),
        pytest.param(
            {
                "manifest": {},
                "succeed": True,
                "releases": [],
            },
            id="no_releases"
        ),
    ],
)
async def test_hacs_action_integration(
    test_case: dict,
    request: pytest.FixtureRequest,
    caplog: pytest.LogCaptureFixture,
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
    capsys: pytest.CaptureFixture[str],
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
    envpatch = {
        "INPUT_GITHUB_TOKEN": TOKEN,
        "INPUT_REPOSITORY": "hacs-test-org/integration-basic",
        "INPUT_CATEGORY": "integration",
    }

    response_mocker.add(
        "https://brands.home-assistant.io/domains.json",
        response=MockedResponse(status=200, content={"custom": ["example"]}),
    )
    response_mocker.add(
        "https://raw.githubusercontent.com/hacs-test-org/integration-basic/main/custom_components/example/manifest.json",
        response=MockedResponse(
            status=200,
            content=json.dumps({**basemanifest, **test_case["manifest"]}),
            keep=True,
        ),
    )

    if (releases := test_case["releases"]) is not None:
        response_mocker.add(
            "https://api.github.com/repos/hacs-test-org/integration-basic/releases",
            response=MockedResponse(
                status=200,
                content=releases
            ),
        )

    with mock.patch.dict(os.environ, envpatch), mock.patch("builtins.exit", mock.MagicMock()):
        from action.action import preflight

        await preflight()

    assert (
        "All (8) checks passed" if test_case["succeed"] else "1/8 checks failed") in caplog.text

    splitlines = [f"<{line.rsplit(' <')[1]}" for line in caplog.text.split(
        "\n") if " <" in line]

    snapshots.assert_match(
        "\n".join(
            splitlines[0:2] +
            sorted(splitlines[2:-2]) + splitlines[-2:]
            + [capsys.readouterr().out]
        ),
        f"action/{current_function_name()}/{request.node.callspec.id}.log",
    )
