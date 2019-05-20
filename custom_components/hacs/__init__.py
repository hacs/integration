"""
Custom element manager for community created elements.

For more details about this component, please refer to the documentation at
https://github.com/custom-components/hacs (eventually)

For now:
in configuration.yaml:
hacs:
  token: xxxxxxxxxxxxxxxxxx
-------------------------------------
The token is a GitHub Access token, you can create one here:
https://github.com/settings/tokens
You don't have to check any of the boxes.
"""
import logging
import os.path
import json
import asyncio
from datetime import timedelta
import voluptuous as vol
from homeassistant.const import EVENT_HOMEASSISTANT_START
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_time_interval
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
)
from custom_components.hacs.element import Element
from custom_components.hacs.handler.storage import (
    get_data_from_store,
    write_to_data_store,
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

INTERVAL = timedelta(minutes=500)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required("token"): cv.string})}, extra=vol.ALLOW_EXTRA
)


async def async_setup(hass, config):  # pylint: disable=unused-argument
    """Set up this component."""
    _LOGGER.info(STARTUP)
    config_dir = hass.config.path()
    github_token = config[DOMAIN]["token"]
    commander = HacsCommander(hass, github_token)

    # Check if custom_updater exists
    for location in CUSTOM_UPDATER_LOCATIONS:
        if os.path.exists(location.format(config_dir)):
            msg = CUSTOM_UPDATER_WARNING.format(location.format(config_dir))
            _LOGGER.critical(msg)
            # return False

    # Setup background tasks
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, commander.startup_tasks())

    # Register the views
    hass.http.register_view(CommunityOverview(hass))
    hass.http.register_view(CommunityElement(hass))
    hass.http.register_view(CommunityStore(hass))
    hass.http.register_view(CommunityPlugin(hass))
    hass.http.register_view(CommunitySettings(hass))
    hass.http.register_view(CommunityAPI(hass))

    hass.data[DOMAIN_DATA] = {}
    hass.data[DOMAIN_DATA]["commander"] = commander

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


class HacsCommander:
    """HACS Commander class."""

    def __init__(self, hass, github_token):
        """Initialize HacsCommander"""
        import github

        self.hass = hass
        self.git = github.Github(github_token)
        self.skip = SKIP

    async def startup_tasks(self):
        """Run startup_tasks."""
        _LOGGER.debug("Runing startup_tasks.")
        custom_log_level = {"custom_components.hacs": "debug"}
        await self.hass.services.async_call("logger", "set_level", custom_log_level)
        async_track_time_interval(self.hass, self.repetetive_tasks, INTERVAL)

        _LOGGER.info("Loading existing data.")
        # Ready up hass.data
        returndata = await get_data_from_store(self.hass.config.path())
        if not returndata.get("elements"):
            self.hass.data[DOMAIN_DATA]["elements"] = {}
            self.hass.data[DOMAIN_DATA]["repos"] = {"integration": [], "plugin": []}
            self.hass.data[DOMAIN_DATA]["hacs"] = {"local": VERSION, "remote": None}
            await self.repetetive_tasks()
        else:
            self.hass.data[DOMAIN_DATA]["elements"] = returndata["elements"]
            self.hass.data[DOMAIN_DATA]["repos"] = returndata["repos"]
            self.hass.data[DOMAIN_DATA]["hacs"] = returndata["hacs"]

        # Reset restart_pending flag
        self.hass.data[DOMAIN_DATA]["hacs"]["restart_pending"] = False
        for element in self.hass.data[DOMAIN_DATA]["elements"]:
            element = self.hass.data[DOMAIN_DATA]["elements"][element]
            element.restart_pending = False
            self.hass.data[DOMAIN_DATA]["elements"][element.element_id] = element
        await write_to_data_store(self.hass.config.path(), self.hass.data[DOMAIN_DATA])

    async def repetetive_tasks(self, runas=None):  # pylint: disable=unused-argument
        """Run repetetive tasks."""
        _LOGGER.debug("Run background_tasks.")

        # Check HACS
        try:
            hacs = self.git.get_repo("custom-components/hacs")
            self.hass.data[DOMAIN_DATA]["hacs"]["remote"] = list(hacs.get_releases())[
                0
            ].tag_name
        except Exception as error:  # pylint: disable=broad-except
            _LOGGER.debug(error)

        integration_repos = []
        plugin_repos = []

        # Add integration repos to check list.
        ## Custom repos
        if self.hass.data[DOMAIN_DATA]["repos"].get("integration"):
            for entry in self.hass.data[DOMAIN_DATA]["repos"].get("integration"):
                _LOGGER.debug("Checking custom repo %s", entry)
                repo = entry
                if "http" in repo:
                    repo = repo.split("https://github.com/")[-1]

                if len(repo.split("/")) != 2:
                    _LOGGER.error("%s is not valid", entry)
                    continue

                try:
                    repo = self.git.get_repo(repo)
                    if not repo.archived or repo.full_name not in self.skip:
                        integration_repos.append(repo.full_name)
                except Exception as error:  # pylint: disable=broad-except
                    _LOGGER.error(error)

        ## Org repos
        for repo in list(self.git.get_organization("custom-components").get_repos()):
            if repo.archived:
                continue
            if repo.full_name in self.skip:
                continue
            integration_repos.append(repo.full_name)

        # Add plugin repos to check list.
        ## Custom repos
        if self.hass.data[DOMAIN_DATA]["repos"].get("plugin"):
            for entry in self.hass.data[DOMAIN_DATA]["repos"].get("plugin"):
                _LOGGER.debug("Checking custom repo %s", entry)
                repo = entry
                if "http" in repo:
                    repo = repo.split("https://github.com/")[-1]

                if len(repo.split("/")) != 2:
                    _LOGGER.error("%s is not valid", entry)
                    continue

                try:
                    repo = self.git.get_repo(repo)
                    if not repo.archived or repo.full_name not in self.skip:
                        plugin_repos.append(repo.full_name)
                except Exception as error:  # pylint: disable=broad-except
                    _LOGGER.error(error)

        ## Org repos
        for repo in list(self.git.get_organization("custom-cards").get_repos()):
            if repo.archived:
                continue
            if repo.full_name in self.skip:
                continue
            plugin_repos.append(repo.full_name)

        _LOGGER.debug(integration_repos)

        for repo in integration_repos:
            await load_integrations_from_git(self.hass, repo)

        _LOGGER.debug(plugin_repos)

        self.hass.async_create_task(
            self.prosess_repos(integration_repos, "integration")
        )
        self.hass.async_create_task(self.prosess_repos(plugin_repos, "plugin"))

    async def prosess_repos(self, repos, repo_type):
        """Prosess repos."""
        if repo_type == "integraion":
            for repo in repos:
                await load_integrations_from_git(self.hass, repo)
        elif repo_type == "plugin":
            for repo in repos:
                await load_plugins_from_git(self.hass, repo)
        await write_to_data_store(self.hass.config.path(), self.hass.data[DOMAIN_DATA])
