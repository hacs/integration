"""Deprecated functions, should be fine to remove."""


async def add_services(hacs):
    """Add services."""
    # Service registration
    async def service_hacs_install(call):
        """Install a repository."""
        repository = str(call.data["repository"])
        if repository not in hacs().store.repositories:
            hacs.logger.error("%s is not a konwn repository!", repository)
            return
        repository = hacs().store.repositories[repository]
        await repository.install()

    async def service_hacs_register(call):
        """register a repository."""
        repository = call.data["repository"]
        repository_type = call.data["repository_type"]
        if await hacs().is_known_repository(repository):
            hacs.logger.error("%s is already a konwn repository!", repository)
            return
        await hacs().register_new_repository(repository_type, repository)

    async def service_hacs_load(call):
        """register a repository."""
        from homeassistant.loader import async_get_custom_components

        del hacs.hass.data["custom_components"]
        await async_get_custom_components(hacs.hass)

    hacs.hass.services.async_register("hacs", "install", service_hacs_install)
    hacs.hass.services.async_register("hacs", "register", service_hacs_register)
    hacs.hass.services.async_register("hacs", "load", service_hacs_load)


# This should probably be in a dedicated test "package"
async def test_repositories(hacs):
    """Test repositories."""
    await hacs().register_repository("ludeeus/theme-hacs", "theme")
    await hacs().register_repository("ludeeus/ps-hacs", "python_script")
    await hacs().register_repository("ludeeus/integration-hacs", "integration")
    await hacs().register_repository(
        "rgruebel/ha_zigbee2mqtt_networkmap", "integration"
    )
    await hacs().register_repository("ludeeus/ad-hacs", "appdaemon")
    await hacs().register_repository("jonkristian/entur-card", "plugin")  # Dist
    await hacs().register_repository("kalkih/mini-media-player", "plugin")  # Release
    await hacs().register_repository("custom-cards/monster-card", "plugin")  # root
