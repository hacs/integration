from custom_components.hacs.helpers.functions.is_safe_to_remove import is_safe_to_remove


def test_is_safe_to_remove(hacs):
    assert is_safe_to_remove("/test")

    assert not is_safe_to_remove(
        f"{hacs.system.config_path}/{hacs.configuration.theme_path}/"
    )

    assert not is_safe_to_remove(f"{hacs.system.config_path}/custom_components/")

    assert not is_safe_to_remove(f"{hacs.system.config_path}/custom_components")
