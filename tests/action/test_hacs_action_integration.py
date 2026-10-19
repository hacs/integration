"""Tests for the HACS action."""
import base64
import json
import os
from unittest import mock

import pytest

from tests.common import (
    TOKEN,
    MockedResponse,
    ResponseMocker,
    current_function_name,
    normalize_voluptuous_paths,
)
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
                "manifest": {"categories": ["unknown"]},
                "succeed": False,
                "releases": None,
            },
            id="bad_categories"
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
    manifest = json.dumps({**basemanifest, **test_case["manifest"]})
    response_mocker.add(
        "https://api.github.com/repos/hacs-test-org/integration-basic/contents/custom_components/example/manifest.json",
        response=MockedResponse(
            status=200,
            content={"content": base64.b64encode(manifest.encode()).decode()},
            headers={"Content-Type": "application/json"},
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
        "All (10) checks passed" if test_case["succeed"] else "1/10 checks failed") in caplog.text

    splitlines = [f"<{line.rsplit(' <')[1]}" for line in caplog.text.split(
        "\n") if " <" in line]

    snapshots.assert_match(
        normalize_voluptuous_paths(
            "\n".join(
                splitlines[0:2] +
                sorted(splitlines[2:-2]) + splitlines[-2:]
                + [capsys.readouterr().out]
            )
        ),
        f"action/{current_function_name()}/{request.node.callspec.id}.log",
    )


async def test_hacs_action_private_repository(
    caplog: pytest.LogCaptureFixture,
    response_mocker: ResponseMocker,
):
    """Test the action refuses a private repository before validating it."""
    with open(
        "tests/fixtures/proxy/api.github.com/repos/hacs-test-org/integration-basic.json"
    ) as repository_file:
        repository = json.load(repository_file)

    response_mocker.add(
        "https://api.github.com/repos/hacs-test-org/integration-basic",
        response=MockedResponse(status=200, content={**repository, "private": True}),
    )
    envpatch = {
        "INPUT_GITHUB_TOKEN": TOKEN,
        "INPUT_REPOSITORY": "hacs-test-org/integration-basic",
        "INPUT_CATEGORY": "integration",
    }

    with mock.patch.dict(os.environ, envpatch):
        from action.action import preflight

        with (
            mock.patch("builtins.exit", mock.MagicMock(side_effect=SystemExit)),
            pytest.raises(SystemExit),
        ):
            await preflight()

    assert (
        "hacs-test-org/integration-basic is private, "
        "the HACS action can only validate public repositories."
    ) in caplog.text
    assert "checks passed" not in caplog.text
