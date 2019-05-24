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
import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_START, __version__ as HAVERSION
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_time_interval, async_call_later
from custom_components.hacs.hacs import HACS
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
    SKIP,
    DATA_SCHEMA,
)
from custom_components.hacs.element import add_new_element
from custom_components.hacs.handler.storage import (
    get_data_from_store,
    write_to_data_store,
    data_migration,
)
from custom_components.hacs.handler.update import (
    load_integrations_from_git,
    load_plugins_from_git,
)
from custom_components.hacs.frontend.views import (
    CommunityOverview,
    CommunityElement,
    CommunityPlugin,
    CommunityStore,
    CommunitySettings,
    CommunityAPI,
)

DOMAIN = "{}".format(NAME_SHORT.lower())

# TODO: Requirements are not loaded from manifest, needs investigation.
REQUIREMENTS = ["PyGithub>=1.43.6", "aiofiles"]

_LOGGER = logging.getLogger(__name__)

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
    HACS.hass = hass
    HACS.github = github.Github(github_token, timeout=5, retry=2)
    HACS.blacklist = SKIP

    # Check if custom_updater exists
    for location in CUSTOM_UPDATER_LOCATIONS:
        if os.path.exists(location.format(config_dir)):
            msg = CUSTOM_UPDATER_WARNING.format(location.format(config_dir))
            _LOGGER.critical(msg)
            return False

    # Check if HA is the required version.
    if int(HAVERSION.split(".")[1]) < 92:
        _LOGGER.critical("You need HA version 92 or newer to use this integration.")
        return False

    # Setup startup tasks
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, commander.startup_tasks())

    # Register the views
    hass.http.register_view(CommunityOverview(hass, HACS))
    hass.http.register_view(CommunityElement(hass, HACS))
    hass.http.register_view(CommunityStore(hass, HACS))
    hass.http.register_view(CommunityPlugin(hass, HACS))
    hass.http.register_view(CommunitySettings(hass, HACS))
    hass.http.register_view(CommunityAPI(hass, HACS))

    HACS.data["commander"] = commander

    # Add to sidepanel
    await hass.components.frontend.async_register_built_in_panel(
        "iframe",
        IFRAME["title"],
        IFRAME["icon"],
        IFRAME["path"],
        {"url": IFRAME["url"]},
        require_admin=IFRAME["require_admin"],
    )

    # Mischief managed!
    return True


class HacsCommander(HACS):
    """HACS Commander class."""

    async def startup_tasks(self):
        """Run startup_tasks."""
        self.task_running = True
        _LOGGER.debug("Runing startup tasks.")

        custom_log_level = {"custom_components.hacs": "debug"}
        await self.hass.services.async_call("logger", "set_level", custom_log_level)

        await self.setup_recuring_tasks()

        _LOGGER.info("Trying to load existing data.")
        returndata = await get_data_from_store(self.hass,self.github)

        if not returndata.get("elements"):
            _LOGGER.info(
                "Expected data did not exist running initial setup, this will take some time."
            )
            self.data["elements"] = {}
            self.data["repos"] = {"integration": [], "plugin": []}
            self.data["hacs"] = {"local": VERSION, "remote": None, "schema": DATA_SCHEMA}
            #self.hass.async_create_task(self.full_element_scan())
            async_call_later(self.hass, 1, self.full_element_scan)

        else:
            if not returndata.get("hacs", {}).get("schema"):
                await data_migration(self.hass,self.github)
            elif returndata.get("hacs", {}).get("schema") != DATA_SCHEMA:
                await data_migration(self.hass,self.github)
            else:
                self.data["elements"] = returndata["elements"]
                self.data["repos"] = returndata["repos"]
                self.data["hacs"] = returndata["hacs"]

        # Make sure we have the correct version
        self.data["hacs"]["local"] = VERSION

        # Reset restart_pending flag
        self.data["hacs"]["restart_pending"] = False
        for element in self.data["elements"]:
            element = self.data["elements"][element]
            element.restart_pending = False
            self.data["elements"][element.element_id] = element

        await self.check_for_hacs_update()

        # Update installed element data on startup
        for element in self.data["elements"]:
            element_object = self.data["elements"][element]
            if element_object.isinstalled:
                #self.hass.async_create_task(element_object.update_element())
                await element_object.update_element()
                await asyncio.sleep(2) #  Breathing room


        await write_to_data_store(self.hass.config.path(), self.data)
        self.task_running = False

    async def check_for_hacs_update(self, notarealargument=None):
        """Check for hacs update."""
        _LOGGER.debug("Checking for HACS updates...")
        try:
            hacs =self.github.get_repo("custom-components/hacs")
            self.data["hacs"]["remote"] = list(hacs.get_releases())[
                0
            ].tag_name
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug(error)

    def get_repos(self):
        """Get org and custom repos."""

        integration_repos = self.get_repos_integration()
        plugin_repos = self.get_repos_plugin()

        _LOGGER.debug(integration_repos)
        _LOGGER.debug(plugin_repos)

        return integration_repos, plugin_repos

    def get_repos_integration(self):
        """Get org and custom integration repos."""
        repos = []

        # Custom repos
        if self.data["repos"].get("integration"):
            for entry in self.data["repos"].get("integration"):
                _LOGGER.debug("Checking custom repo %s", entry)
                repo = entry
                if "http" in repo:
                    repo = repo.split("https://github.com/")[-1]

                if len(repo.split("/")) != 2:
                    _LOGGER.error("%s is not valid", entry)
                    continue

                try:
                    repo =self.github.get_repo(repo)
                    if not repo.archived or repo.full_name not in self.blacklist:
                        repos.append(repo.full_name)
                except Exception as error:  # pylint: disable=broad-except
                    _LOGGER.error(error)

        # Org repos
        for repo in list(self.github.get_organization("custom-components").get_repos()):
            if repo.archived:
                continue
            if repo.full_name in self.blacklist:
                continue
            repos.append(repo.full_name)

        return repos

    def get_repos_plugin(self):
        """Get org and custom plugin repos."""
        repos = []

        ## Custom repos
        if self.data["repos"].get("plugin"):
            for entry in self.data["repos"].get("plugin"):
                _LOGGER.debug("Checking custom repo %s", entry)
                repo = entry
                if "http" in repo:
                    repo = repo.split("https://github.com/")[-1]

                if len(repo.split("/")) != 2:
                    _LOGGER.error("%s is not valid", entry)
                    continue

                try:
                    repo =self.github.get_repo(repo)
                    if not repo.archived or repo.full_name not in self.blacklist:
                        repos.append(repo.full_name)
                except Exception as error:  # pylint: disable=broad-except
                    _LOGGER.error(error)

        ## Org repos
        for repo in list(self.github.get_organization("custom-cards").get_repos()):
            if repo.archived:
                continue
            if repo.full_name in self.blacklist:
                continue
            repos.append(repo.full_name)

        return repos

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
            for element in repos[element_type]:
                if element in self.blacklist:
                    continue

                if element not in self.data["elements"]:
                    await add_new_element(self, element_type, element)

                else:
                    await self.data["elements"][element].update_element()

                await asyncio.sleep(2) #  Breathing room

        await write_to_data_store(self.hass.config.path(), self.data)
        _LOGGER.debug(f'Completed full element refresh scan in {(datetime.now() - start_time).seconds} seconds')
        self.task_running = False
