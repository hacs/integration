from custom_components.hacs.base import HacsBase
from custom_components.hacs.utils import path


def test_is_safe(hacs: HacsBase) -> None:
    assert path.is_safe(hacs, "/test")
    assert not path.is_safe(hacs, f"{hacs.core.config_path}/{hacs.configuration.theme_path}/")
    assert not path.is_safe(hacs, f"{hacs.core.config_path}/custom_components/")
    assert not path.is_safe(hacs, f"{hacs.core.config_path}/custom_components")
