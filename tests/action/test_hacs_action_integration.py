"""Tests for the HACS action."""
import base64
import json
import os
from unittest import mock

import pytest

from tests.common import TOKEN, MockedResponse, ResponseMocker, current_function_name
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "key,manifest,succeed",
    (
        ("bad_documentation", {"documentation": None}, False),
        ("bad_issue_tracker", {"issue_tracker": None}, False),
        ("valid_manifest1", {}, True),
    ),
)
async def test_hacs_action_integration(
    key: str,
    manifest: dict[str, str | bool | None],
    succeed: bool,
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
            content=json.dumps({**basemanifest, **manifest}),
            keep=True,
        ),
    )

    with mock.patch.dict(os.environ, envpatch), mock.patch("builtins.exit", mock.MagicMock()):
        from action.action import preflight

        await preflight()

    assert ("All (8) checks passed" if succeed else "1/8 checks failed") in caplog.text

    splitlines = [f"<{line.rsplit(' <')[1]}" for line in caplog.text.split(
        "\n") if " <" in line]

    snapshots.assert_match(
        "\n".join(splitlines[0:2] +
                  sorted(splitlines[2:-2]) + splitlines[-2:]),
        f"action/{current_function_name()}/{key}.log",
    )
