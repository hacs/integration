import pytest

from custom_components.hacs.base import HacsBase
from custom_components.hacs.utils import path


def test_is_safe(hacs: HacsBase) -> None:
    assert path.is_safe(hacs, "/test")
    assert not path.is_safe(hacs, f"{hacs.core.config_path}/{hacs.configuration.theme_path}/")
    assert not path.is_safe(hacs, f"{hacs.core.config_path}/custom_components/")
    assert not path.is_safe(hacs, f"{hacs.core.config_path}/custom_components")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("example.js", True),
        ("sub/dir/example.js", True),
        ("userfiles", True),
        ("..", False),
        ("../example.js", False),
        ("sub/../../example.js", False),
        ("/etc/passwd", False),
        ("\\windows\\style", False),
        ("sub\\..\\..\\example.js", False),
        (None, False),
        (123, False),
    ],
)
def test_is_safe_relative_path(value, expected: bool) -> None:
    assert path.is_safe_relative_path(value) is expected
