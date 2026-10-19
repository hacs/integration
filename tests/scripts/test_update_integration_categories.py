"""Test update integration categories."""

from unittest.mock import MagicMock, patch

from scripts.update_integration_categories import (
    CATEGORIES_URL,
    HEADER,
    update_integration_categories,
)


def test_update_integration_categories(tmp_path):
    """Test that categories and subcategories are written sorted."""
    response = MagicMock()
    response.json.return_value = [
        {"slug": "energy", "subcategories": [{"slug": "solar"}, {"slug": "ev_charging"}]},
        {"slug": "climate", "subcategories": []},
    ]
    output = tmp_path / "integration_categories.py"

    with patch("scripts.update_integration_categories.requests.get", return_value=response) as get:
        update_integration_categories(output)

    get.assert_called_once_with(CATEGORIES_URL, timeout=30)
    assert output.read_text(encoding="utf-8") == (
        f'{HEADER}    "climate",\n    "energy",\n    "energy.ev_charging",\n    "energy.solar",\n}}\n'
    )
