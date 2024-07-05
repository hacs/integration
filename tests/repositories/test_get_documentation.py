"""Tests for the get_documentation method on the HacsRepository class."""

from __future__ import annotations

import json
from typing import Any

import pytest
from slugify import slugify

from custom_components.hacs.base import HacsBase
from custom_components.hacs.repositories.base import HacsRepository

from tests.common import ResponseMocker, client_session_proxy
from tests.conftest import SnapshotFixture


@pytest.mark.parametrize(
    "data",
    [
        {"installed": True, "installed_version": "1.0.0"},
        {"installed": True, "installed_version": "1.0.0","last_version": "2.0.0"},
        {"installed": False, "last_version": "2.0.0"},
        {"installed": False, "last_version": "99.99.99"},
    ],
)
async def test_repository_get_documentation(
    hacs: HacsBase,
    data: dict[str, Any],
    response_mocker: ResponseMocker,
    snapshots: SnapshotFixture,
):
    repository = HacsRepository(hacs=hacs)
    repository.data.full_name = "hacs-test-org/integration-basic"
    for key, value in data.items():
        setattr(repository.data, key, value)

    hacs.session = await client_session_proxy(hacs.hass)
    docs = await repository.get_documentation(filename="README.md", version=None)
    snapshots.assert_match(
        docs or "None",
        f"{repository.data.full_name}/get_documentation/{slugify(json.dumps(data), separator="_")}.md",
    )
