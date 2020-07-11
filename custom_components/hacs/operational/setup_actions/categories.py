from custom_components.hacs.share import get_hacs


def _setup_extra_stores():
    """Set up extra stores in HACS if enabled in Home Assistant."""
    hacs = get_hacs()
    if "python_script" in hacs.hass.config.components:
        if "python_script" not in hacs.common.categories:
            hacs.common.categories.append("python_script")

    if (
        hacs.hass.services._services.get("frontend", {}).get("reload_themes")
        is not None
    ):
        if "theme" not in hacs.common.categories:
            hacs.common.categories.append("theme")


async def async_setup_extra_stores():
    """Async wrapper for setup_extra_stores"""
    hacs = get_hacs()
    await hacs.hass.async_add_executor_job(_setup_extra_stores)
