"""Starting setup task: extra stores."""
from custom_components.hacs.const import ELEMENT_TYPES
from ...share import get_hacs
from ...enums import HacsCategory, HacsSetupTask


def _setup_extra_stores():
    """Set up extra stores in HACS if enabled in Home Assistant."""
    hacs = get_hacs()
    hacs.log.debug("Starting setup task: Extra stores")
    hacs.common.categories = set()
    for category in ELEMENT_TYPES:
        enable_category(hacs, HacsCategory(category))

    if HacsCategory.PYTHON_SCRIPT in hacs.hass.config.components:
        if HacsCategory.PYTHON_SCRIPT not in hacs.common.categories:
            enable_category(hacs, HacsCategory.PYTHON_SCRIPT)

    if (
        hacs.hass.services._services.get("frontend", {}).get("reload_themes")
        is not None
    ):
        if HacsCategory.THEME not in hacs.common.categories:
            enable_category(hacs, HacsCategory.THEME)

    if hacs.configuration.appdaemon:
        enable_category(hacs, HacsCategory.APPDAEMON)
    if hacs.configuration.netdaemon:
        enable_category(hacs, HacsCategory.NETDAEMON)


async def async_setup_extra_stores():
    """Async wrapper for setup_extra_stores"""
    hacs = get_hacs()
    hacs.log.info("setup task %s", HacsSetupTask.CATEGORIES)
    await hacs.hass.async_add_executor_job(_setup_extra_stores)


def enable_category(hacs, category: HacsCategory):
    """Add category."""
    hacs.log.debug("Enable category: %s", category)
    hacs.common.categories.add(category)
