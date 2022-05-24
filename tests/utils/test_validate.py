from awesomeversion import AwesomeVersion
import pytest
from voluptuous.error import Invalid

from custom_components.hacs.utils.validate import (
    HACS_MANIFEST_JSON_SCHEMA as hacs_json_schema,
)


def test_hacs_manufest_json_schema():
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
        }
    )
    assert hacs_json_schema(
        {
            "name": "My awesome thing",
            "country": "NO",
            "homeassistant": "0.99.9",
            "persistent_directory": "userfiles",
        }
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
        }
    )

    with pytest.raises(Invalid, match="extra keys not allowed"):
        hacs_json_schema({"name": "My awesome thing", "not": "valid"})

    with pytest.raises(Invalid, match="Value 'NOT_VALID' is not in"):
        hacs_json_schema({"name": "My awesome thing", "country": "not_valid"})

    with pytest.raises(Invalid, match="Value 'False' is not a string or list."):
        hacs_json_schema({"name": "My awesome thing", "country": False})
