"""Starting setup task: extra stores."""
from ...share import get_hacs
from ...enums import HacsCategory, HacsSetupTask
from ...decorator import announceSetup


def _setup_extra_stores():
    """Set up extra stores in HACS if enabled in Home Assistant."""
    hacs = get_hacs()
    hacs.log.debug("Starting setup task: Extra stores")
    if HacsCategory.PYTHON_SCRIPT in hacs.hass.config.components:
        if HacsCategory.PYTHON_SCRIPT not in hacs.common.categories:
            hacs.common.categories.append(HacsCategory.PYTHON_SCRIPT)

    if (
        hacs.hass.services._services.get("frontend", {}).get("reload_themes")
        is not None
    ):
        if HacsCategory.THEME not in hacs.common.categories:
            hacs.common.categories.append(HacsCategory.THEME)


@announceSetup(HacsSetupTask.CATEGORIES)
async def async_setup_extra_stores():
    """Async wrapper for setup_extra_stores"""
    hacs = get_hacs()
    await hacs.hass.async_add_executor_job(_setup_extra_stores)
