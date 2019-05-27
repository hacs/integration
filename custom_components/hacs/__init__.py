"""
Custom element manager for community created elements.

For more details about this component, please refer to the documentation at
https://custom-components.github.io/hacs/
"""
# pylint: disable=not-an-iterable, unused-argument
import logging
import os.path
import json
import asyncio
from datetime import datetime, timedelta
from pkg_resources import parse_version
import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_START, __version__ as HAVERSION
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from custom_components.hacs.blueprints import HacsBase as hacs, HacsRepositoryIntegration
from custom_components.hacs.const import (
    CUSTOM_UPDATER_LOCATIONS,
    STARTUP,
    PROJECT_URL,
    ISSUE_URL,
    CUSTOM_UPDATER_WARNING,
    NAME_LONG,
    NAME_SHORT,
    DOMAIN_DATA,
    ELEMENT_TYPES,
    VERSION,
    IFRAME,
    BLACKLIST,
    DATA_SCHEMA,
)
from custom_components.hacs.handler.storage import (
    data_migration,
)

from custom_components.hacs.frontend.views import (
    HacsStaticView,
    HacsErrorView,
    HacsPluginView,
    HacsOverviewView,
    HacsStoreView,
    HacsSettingsView,
    HacsRepositoryView,
    HacsAPIView,
)

DOMAIN = "{}".format(NAME_SHORT.lower())

_LOGGER = logging.getLogger('custom_components.hacs')

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required("token"): cv.string})}, extra=vol.ALLOW_EXTRA
)


async def async_setup(hass, config):  # pylint: disable=unused-argument
    """Set up this component."""
    import github
    _LOGGER.info(STARTUP)
    config_dir = hass.config.path()
    github_token = config[DOMAIN]["token"]
    commander = HacsCommander()

    # Add stuff to hacs
    hacs.hass = hass
    hacs.github = github.Github(github_token, timeout=5, retry=2)
    hacs.blacklist = BLACKLIST
    hacs.config_dir = config_dir

    for item in hacs.url_path:
        _LOGGER.critical(f"{item}: {hacs.url_path[item]}")

    # Check if custom_updater exists
    for location in CUSTOM_UPDATER_LOCATIONS:
        if os.path.exists(location.format(config_dir)):
            msg = CUSTOM_UPDATER_WARNING.format(location.format(config_dir))
            _LOGGER.critical(msg)
            return False

    # Check if HA is the required version.
    if parse_version(HAVERSION) < parse_version('0.92.0'):
        _LOGGER.critical("You need HA version 92 or newer to use this integration.")
        return False

    # Setup startup tasks
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, commander.startup_tasks())

    # Register the views
    hass.http.register_view(HacsStaticView())
    hass.http.register_view(HacsErrorView())
    hass.http.register_view(HacsPluginView())
    hass.http.register_view(HacsStoreView())
    hass.http.register_view(HacsOverviewView())
    hass.http.register_view(HacsSettingsView())
    hass.http.register_view(HacsRepositoryView())
    hass.http.register_view(HacsAPIView())

    hacs.data["commander"] = commander

    # Add to sidepanel
    await hass.components.frontend.async_register_built_in_panel(
        "iframe",
        IFRAME["title"],
        IFRAME["icon"],
        IFRAME["path"],
        {"url": hacs.url_path["overview"]},
        require_admin=IFRAME["require_admin"],
    )

    # Mischief managed!
    return True


class HacsCommander(hacs):
    """HACS Commander class."""

    async def startup_tasks(self):
        """Run startup_tasks."""
        self.task_running = True

        _LOGGER.debug("Runing startup tasks.")

        custom_log_level = {"custom_components.hacs": "debug"}
        await self.hass.services.async_call("logger", "set_level", custom_log_level)

        await self.setup_recuring_tasks()  # TODO: Check this...

        _LOGGER.info("Trying to load existing data.")

        await self.get_data_from_store()

        if not self.repositories:
            _LOGGER.info(
                "Expected data did not exist running initial setup, this will take some time."
            )
            self.repositories = {}
            self.data["hacs"] = {
                "local": VERSION,
                "remote": None,
                "schema": DATA_SCHEMA}
            #self.hass.async_create_task(self.full_element_scan())
            async_call_later(self.hass, 1, self.full_element_scan)

        else:
            _LOGGER.warning("migration logic goes here")

        # Make sure we have the correct version
        self.data["hacs"]["local"] = VERSION

        await self.check_for_hacs_update()

        # Update installed element data on startup
        for element in self.repositories:
            element_object = self.repositories[element]
            if element_object.installed:
                #self.hass.async_create_task(element_object.update_element())
                await element_object.update()
                # TODO await asyncio.sleep(2) #  Breathing room


        await self.full_element_scan()
        self.task_running = False

    async def check_for_hacs_update(self, notarealargument=None):
        """Check for hacs update."""
        _LOGGER.debug("Checking for HACS updates...")
        try:
            repository = self.github.get_repo("custom-components/hacs")
            self.data["hacs"]["remote"] = list(repository.get_releases())[
                0
            ].tag_name
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug(error)

    def get_repos(self):
        """Get org and custom repos."""

        integration_repos = self.get_repos_integration()
        plugin_repos = self.get_repos_plugin()

        return integration_repos, plugin_repos

    def get_repos_integration(self):
        """Get org and custom integration repos."""
        repositories = []

        # Org repos
        for repository in list(self.github.get_organization("custom-components").get_repos()):
            if repository.archived:
                continue
            if repository.full_name in self.blacklist:
                continue
            repositories.append(repository)

        return repositories

    def get_repos_plugin(self):
        """Get org and custom plugin repos."""
        repositories = []
        ## Org repos
        for repository in list(self.github.get_organization("custom-cards").get_repos()):
            if repository.archived:
                continue
            if repository.full_name in self.blacklist:
                continue
            repositories.append(repository)

        return repositories

    async def setup_recuring_tasks(self):
        """Setup recuring tasks."""

        hacs_scan_interval = timedelta(minutes=60)
        full_element_scan_interval = timedelta(minutes=500)

        async_track_time_interval(self.hass, self.check_for_hacs_update, hacs_scan_interval)
        async_track_time_interval(self.hass, self.full_element_scan, full_element_scan_interval)

    async def full_element_scan(self, notarealargument=None):
        """Setup full element refresh scan."""
        self.task_running = True
        start_time = datetime.now()
        integration_repos, plugin_repos = self.get_repos()

        repos = {"integration": integration_repos, "plugin": plugin_repos}

        for element_type in repos:
            for repository in repos[element_type]:
                if repository.full_name in self.blacklist:
                    continue

                if str(repository.id) not in self.repositories:
                    await self.register_new_repository(element_type, repository.full_name)
                else:
                    repository = self.repositories[str(repository.id)]
                    if repository.installed:
                        await repository.update()

        await self.write_to_data_store()
        _LOGGER.debug(f'Completed full element refresh scan in {(datetime.now() - start_time).seconds} seconds')
        self.task_running = False
