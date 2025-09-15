from contextlib import nullcontext as does_not_raise
import re

from awesomeversion import AwesomeVersion
import pytest
from voluptuous.error import Invalid, MultipleInvalid

from custom_components.hacs.utils.validate import (
    HACS_MANIFEST_JSON_SCHEMA as hacs_json_schema,
    INTEGRATION_MANIFEST_JSON_SCHEMA as integration_json_schema,
    VALIDATE_FETCHED_V2_CRITICAL_REPO_SCHEMA,
    VALIDATE_FETCHED_V2_REMOVED_REPO_SCHEMA,
    VALIDATE_FETCHED_V2_REPO_DATA,
    VALIDATE_GENERATED_V2_CRITICAL_REPO_SCHEMA,
    VALIDATE_GENERATED_V2_REMOVED_REPO_SCHEMA,
    VALIDATE_GENERATED_V2_REPO_DATA,
)

from tests.common import fixture


def test_hacs_manifest_json_schema():
    """Test HACS validator."""
    assert hacs_json_schema({"name": "My awesome thing", "homeassistant": "1.2"}) == {
        "name": "My awesome thing",
        "homeassistant": AwesomeVersion(1.2),
    }
    assert hacs_json_schema({"name": "My awesome thing", "hacs": "1.2"}) == {
        "name": "My awesome thing",
        "hacs": AwesomeVersion(1.2),
    }

    assert hacs_json_schema({"name": "My awesome thing", "country": ["NO"]}) == {
        "name": "My awesome thing",
        "country": ["NO"],
    }
    assert hacs_json_schema({"name": "My awesome thing", "country": "NO"}) == {
        "name": "My awesome thing",
        "country": ["NO"],
    }
    assert hacs_json_schema({"name": "My awesome thing", "country": "no"}) == {
        "name": "My awesome thing",
        "country": ["NO"],
    }

    assert hacs_json_schema(
        {
            "name": "My awesome thing",
            "content_in_root": True,
            "filename": "my_super_awesome_thing.js",
            "country": ["NO", "SE", "DK"],
        },
    )
    assert hacs_json_schema(
        {
            "name": "My awesome thing",
            "country": "NO",
            "homeassistant": "0.99.9",
            "persistent_directory": "userfiles",
        },
    )

    assert hacs_json_schema(
        {
            "name": "My awesome thing",
            "content_in_root": True,
            "zip_release": True,
            "filename": "my_super_awesome_thing.js",
            "render_readme": True,
            "country": "NO",
            "homeassistant": "0.99.9",
            "persistent_directory": "userfiles",
        },
    )

    assert hacs_json_schema(
        {
            "name": "My awesome thing",
        },
    )

    with pytest.raises(Invalid, match="extra keys not allowed"):
        hacs_json_schema({"name": "My awesome thing", "not": "valid"})

    with pytest.raises(Invalid, match="Value 'NOT_VALID' is not in"):
        hacs_json_schema({"name": "My awesome thing", "country": "not_valid"})

    with pytest.raises(Invalid, match=re.escape("Value 'False' is not a string or list.")):
        hacs_json_schema({"name": "My awesome thing", "country": False})


def test_integration_json_schema():
    """Test integration manifest."""
    base_data = {
        "issue_tracker": "https://hacs.xyz/",
        "name": "My awesome thing",
        "version": "1.2",
        "domain": "myawesomething",
        "codeowners": ["test"],
        "documentation": "https://hacs.xyz/",
    }

    assert integration_json_schema(base_data)["version"] == AwesomeVersion(1.2)
    assert integration_json_schema(base_data) == base_data

    with pytest.raises(Invalid, match="expected str for dictionary value"):
        integration_json_schema({**base_data, "domain": None})


def test_critical_repo_data_json_schema():
    """Test validating https://data-v2.hacs.xyz/critical/data.json."""
    data = fixture("v2-critical-data.json")
    for repo in data:
        VALIDATE_FETCHED_V2_CRITICAL_REPO_SCHEMA(repo)
    VALIDATE_GENERATED_V2_CRITICAL_REPO_SCHEMA(data)


@pytest.mark.parametrize(
    ("data", "expectation_1", "expectation_2"),
    [
        # Good data
        (
            {"repository": "test", "reason": "blah", "link": "https://blah"},
            does_not_raise(),
            does_not_raise(),
        ),
        # Missing required key
        (
            {},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            {"repository": "test", "reason": "blah"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            {"repository": "test", "link": "https://blah"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            {"reason": "blah", "link": "https://blah"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        # Wrong data type
        (
            {"repository": 123, "reason": "blah", "link": "https://blah"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            {"repository": "test", "reason": 123, "link": "https://blah"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            {"repository": "test", "reason": "blah", "link": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        # Extra key
        (
            {"repository": "test", "reason": "blah",
                "link": "https://blah", "extra": "key"},
            does_not_raise(),
            pytest.raises(Invalid),
        ),
    ],
)
def test_critical_repo_data_json_schema_bad_data(data: dict, expectation_1, expectation_2):
    """Test validating https://data-v2.hacs.xyz/critical/data.json."""
    with expectation_1:
        VALIDATE_FETCHED_V2_CRITICAL_REPO_SCHEMA(data)
    with expectation_2:
        VALIDATE_GENERATED_V2_CRITICAL_REPO_SCHEMA([data])


@pytest.mark.parametrize(
    "category",
    [
        "appdaemon",
        "integration",
        "plugin",
        "python_script",
        "template",
        "theme",
    ],
)
def test_repo_data_json_schema(category: str):
    """Test validating https://data-v2.hacs.xyz/<category>/data.json."""
    data = fixture(f"v2-{category}-data.json")
    for repo in data.values():
        VALIDATE_FETCHED_V2_REPO_DATA[category](repo)
    VALIDATE_GENERATED_V2_REPO_DATA[category](data)


GOOD_COMMON_DATA = {
    "description": "abc",
    "etag_repository": "blah",
    "full_name": "blah",
    "last_commit": "abc",
    "last_fetched": 0,
    "last_updated": "blah",
    "manifest": {},
}

GOOD_INTEGRATION_DATA = {
    "description": "abc",
    "domain": "abc",
    "etag_repository": "blah",
    "full_name": "blah",
    "last_commit": "abc",
    "last_fetched": 0,
    "last_updated": "blah",
    "manifest": {},
    "manifest_name": "abc",
}


def without(d: dict, key: str) -> dict:
    """Return a copy of d without key."""
    d = dict(d)
    d.pop(key)
    return d


@pytest.mark.parametrize(
    ("categories", "data", "expectation_1", "expectation_2"),
    [
        # Good data
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA,
            does_not_raise(),
            does_not_raise(),
        ),
        # Test we allow at least one of last_commit or last_version
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            without(GOOD_COMMON_DATA, "last_commit") | {"last_version": "123"},
            does_not_raise(),
            does_not_raise(),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"last_version": "123"},
            does_not_raise(),
            does_not_raise(),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"last_version": "123", "prerelease": "1.2.3"},
            does_not_raise(),
            does_not_raise(),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"last_version": "123", "prerelease": None},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        # Missing required key
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            without(GOOD_COMMON_DATA, "description"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            without(GOOD_COMMON_DATA, "etag_repository"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            without(GOOD_COMMON_DATA, "full_name"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            without(GOOD_COMMON_DATA, "last_commit"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            without(GOOD_COMMON_DATA, "last_fetched"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            without(GOOD_COMMON_DATA, "last_updated"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            without(GOOD_COMMON_DATA, "manifest"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        # Wrong data type in required keys
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"description": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"etag_repository": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"full_name": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"last_commit": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"last_fetched": "blah"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"last_updated": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"manifest": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        # Wrong data type in optional keys
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"downloads": "many"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"etag_releases": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"last_commit": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"last_version": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"open_issues": "many"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"stargazers_count": "many"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"topics": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        # Extra key
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            GOOD_COMMON_DATA | {"extra": "key"},
            does_not_raise(),
            pytest.raises(Invalid),
        ),
        # Good data
        (
            ["integration"],
            GOOD_INTEGRATION_DATA,
            does_not_raise(),
            does_not_raise(),
        ),
        # Test we allow at least one of last_commit or last_version
        (
            ["integration"],
            without(GOOD_INTEGRATION_DATA, "last_commit") | {
                "last_version": "123"},
            does_not_raise(),
            does_not_raise(),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"last_version": "123"},
            does_not_raise(),
            does_not_raise(),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {
                "last_version": "123", "prerelease": "1.2.3"},
            does_not_raise(),
            does_not_raise(),
        ),
        # Missing required key
        (
            ["integration"],
            without(GOOD_INTEGRATION_DATA, "description"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            without(GOOD_INTEGRATION_DATA, "domain"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            without(GOOD_INTEGRATION_DATA, "etag_repository"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            without(GOOD_INTEGRATION_DATA, "full_name"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            without(GOOD_INTEGRATION_DATA, "last_commit"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            without(GOOD_INTEGRATION_DATA, "last_fetched"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            without(GOOD_INTEGRATION_DATA, "last_updated"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            without(GOOD_INTEGRATION_DATA, "manifest"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            without(GOOD_INTEGRATION_DATA, "manifest_name"),
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        # Wrong data type in required keys
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"domain": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"description": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"etag_repository": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"full_name": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"last_commit": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"last_fetched": "blah"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"last_updated": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"manifest": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"manifest_name": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        # Wrong data type in optional keys
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"downloads": "many"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"etag_releases": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"last_commit": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"last_version": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"open_issues": "many"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"stargazers_count": "many"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"topics": 123},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        # Extra key
        (
            ["integration"],
            GOOD_INTEGRATION_DATA | {"extra": "key"},
            does_not_raise(),
            pytest.raises(Invalid),
        ),
    ],
)
def test_repo_data_json_schema_bad_data(
    categories: list[str],
    data: dict,
    expectation_1,
    expectation_2,
):
    """Test validating https://data-v2.hacs.xyz/xxx/data.json."""
    for category in categories:
        with expectation_1:
            VALIDATE_FETCHED_V2_REPO_DATA[category](data)
        with expectation_2:
            VALIDATE_GENERATED_V2_REPO_DATA[category]({"test_repo": data})


@pytest.mark.parametrize(
    ("categories", "data"),
    [
        # This has multiple errors:
        # - No last_commit or last_version
        # - No description
        # - full_name is wrong type
        (
            ["appdaemon", "plugin", "python_script", "template", "theme"],
            {
                "etag_repository": "blah",
                "full_name": 123,
                "last_fetched": 0,
                "last_updated": "blah",
                "manifest": {},
            },
        ),
        (
            ["integration"],
            {
                "domain": "abc",
                "etag_repository": "blah",
                "full_name": 123,
                "last_fetched": 0,
                "last_updated": "blah",
                "manifest": {},
                "manifest_name": "abc",
            },
        ),
    ],
)
def test_repo_data_json_schema_multiple_bad_data(categories: list[str], data):
    """Test validating https://data-v2.hacs.xyz/xxx/data.json with multiple errors.

    This tests we get both dict-based schema errors and custom validation errors.
    """
    expected_errors_1 = {
        ("expected str", ("full_name",)),
        ("required key not provided", ("description",)),
        ("Expected at least one of [`last_commit`, `last_version`], got none", ()),
    }
    expected_errors_2 = {
        ("expected str", ("test_repo", "full_name")),
        ("required key not provided", ("test_repo", "description")),
        ("Expected at least one of [`last_commit`, `last_version`], got none", (
            "test_repo",)),
    }
    for category in categories:
        with pytest.raises(MultipleInvalid) as exc_info:
            VALIDATE_FETCHED_V2_REPO_DATA[category](data)
        msgs = [(err.msg, tuple(err.path)) for err in exc_info.value.errors]
        assert len(msgs) == 3
        assert set(msgs) == expected_errors_1

        with pytest.raises(MultipleInvalid) as exc_info:
            VALIDATE_GENERATED_V2_REPO_DATA[category]({"test_repo": data})
        msgs = [(err.msg, tuple(err.path)) for err in exc_info.value.errors]
        assert len(msgs) == 3
        assert set(msgs) == expected_errors_2


def test_removed_repo_data_json_schema():
    """Test validating https://data-v2.hacs.xyz/removed/data.json."""
    data = fixture("v2-removed-data.json")
    for repo in data:
        VALIDATE_FETCHED_V2_REMOVED_REPO_SCHEMA(repo)
    VALIDATE_GENERATED_V2_REMOVED_REPO_SCHEMA(data)


@pytest.mark.parametrize(
    ("data", "expectation_1", "expectation_2"),
    [
        # Good data
        ({"removal_type": "critical", "repository": "test"},
         does_not_raise(), does_not_raise()),
        # Missing required key
        ({}, pytest.raises(Invalid), pytest.raises(Invalid)),
        ({"repository": "test"}, pytest.raises(Invalid), pytest.raises(Invalid)),
        ({"removal_type": "critical"}, pytest.raises(
            Invalid), pytest.raises(Invalid)),
        # Wrong data type
        (
            {"link": 123, "reason": "blah",
                "removal_type": "critical", "repository": "test"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            {
                "link": "https://blah",
                "reason": 123,
                "removal_type": "critical",
                "repository": "test",
            },
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            {"link": "https://blah", "reason": "blah",
                "removal_type": 123, "repository": "test"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            {"link": "https://blah", "reason": "blah",
                "removal_type": "bad", "repository": "test"},
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        (
            {
                "link": "https://blah",
                "reason": "blah",
                "removal_type": "critical",
                "repository": 123,
            },
            pytest.raises(Invalid),
            pytest.raises(Invalid),
        ),
        # Extra key
        (
            {
                "link": "https://blah",
                "reason": "blah",
                "removal_type": "critical",
                "repository": "test",
                "extra": "key",
            },
            does_not_raise(),
            pytest.raises(Invalid),
        ),
    ],
)
def test_removed_repo_data_json_schema_bad_data(data: dict, expectation_1, expectation_2):
    """Test validating https://data-v2.hacs.xyz/critical/data.json."""
    with expectation_1:
        VALIDATE_FETCHED_V2_REMOVED_REPO_SCHEMA(data)
    with expectation_2:
        VALIDATE_GENERATED_V2_REMOVED_REPO_SCHEMA([data])
