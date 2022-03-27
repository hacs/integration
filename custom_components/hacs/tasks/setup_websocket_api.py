"""Register WS API endpoints for HACS."""
from __future__ import annotations

import sys

from aiogithubapi import AIOGitHubAPIException
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api import async_register_command
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from custom_components.hacs.const import DOMAIN

from ..base import HacsBase
from ..enums import HacsStage
from ..exceptions import HacsException
from ..utils import regex
from ..utils.store import async_load_from_store, async_save_to_store
from .base import HacsTask


async def async_setup_task(hacs: HacsBase, hass: HomeAssistant) -> Task:
    """Set up this task."""
    return Task(hacs=hacs, hass=hass)


class Task(HacsTask):
    """Setup the HACS websocket API."""

    stages = [HacsStage.SETUP]

    async def async_execute(self) -> None:
        """Execute the task."""
        async_register_command(self.hass, hacs_settings)
        async_register_command(self.hass, hacs_config)
        async_register_command(self.hass, hacs_repositories)
        async_register_command(self.hass, hacs_repository)
        async_register_command(self.hass, hacs_repository_data)
        async_register_command(self.hass, hacs_status)
        async_register_command(self.hass, hacs_removed)
        async_register_command(self.hass, acknowledge_critical_repository)
        async_register_command(self.hass, get_critical_repositories)
        async_register_command(self.hass, hacs_repository_ignore)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/critical",
        vol.Optional("repository"): cv.string,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def acknowledge_critical_repository(hass, connection, msg):
    """Handle get media player cover command."""
    repository = msg["repository"]

    critical = await async_load_from_store(hass, "critical")
    for repo in critical:
        if repository == repo["repository"]:
            repo["acknowledged"] = True
    await async_save_to_store(hass, "critical", critical)
    connection.send_message(websocket_api.result_message(msg["id"], critical))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/get_critical",
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def get_critical_repositories(hass, connection, msg):
    """Handle get media player cover command."""
    critical = await async_load_from_store(hass, "critical")
    if not critical:
        critical = []
    connection.send_message(websocket_api.result_message(msg["id"], critical))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/config",
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_config(hass, connection, msg):
    """Handle get media player cover command."""
    hacs: HacsBase = hass.data.get(DOMAIN)
    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            {
                "frontend_mode": hacs.configuration.frontend_mode,
                "frontend_compact": hacs.configuration.frontend_compact,
                "onboarding_done": hacs.configuration.onboarding_done,
                "version": hacs.version,
                "frontend_expected": hacs.frontend_version,
                "frontend_running": hacs.frontend_version,
                "dev": hacs.configuration.dev,
                "debug": hacs.configuration.debug,
                "country": hacs.configuration.country,
                "experimental": hacs.configuration.experimental,
                "categories": hacs.common.categories,
            },
        )
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/removed",
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_removed(hass, connection, msg):
    """Get information about removed repositories."""
    hacs: HacsBase = hass.data.get(DOMAIN)
    content = []
    for repo in hacs.repositories.list_removed:
        if repo.repository not in hacs.common.ignored_repositories:
            content.append(repo.to_json())
    connection.send_message(websocket_api.result_message(msg["id"], content))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/repositories",
        vol.Optional("categories"): [str],
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_repositories(hass, connection, msg):
    """Handle get media player cover command."""
    hacs: HacsBase = hass.data.get(DOMAIN)
    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            [
                {
                    "additional_info": repo.additional_info,
                    "authors": repo.data.authors,
                    "available_version": repo.display_available_version,
                    "beta": repo.data.show_beta,
                    "can_install": repo.can_download,
                    "category": repo.data.category,
                    "config_flow": repo.data.config_flow,
                    "country": repo.data.country,
                    "custom": not hacs.repositories.is_default(str(repo.data.id)),
                    "default_branch": repo.data.default_branch,
                    "description": repo.data.description,
                    "domain": repo.data.domain,
                    "downloads": repo.data.downloads,
                    "file_name": repo.data.file_name,
                    "first_install": repo.status.first_install,
                    "full_name": repo.data.full_name,
                    "hide_default_branch": repo.data.hide_default_branch,
                    "hide": repo.data.hide,
                    "homeassistant": repo.data.homeassistant,
                    "id": repo.data.id,
                    "info": None,
                    "installed_version": repo.display_installed_version,
                    "installed": repo.data.installed,
                    "issues": repo.data.open_issues,
                    "javascript_type": None,
                    "last_updated": repo.data.last_updated,
                    "local_path": repo.content.path.local,
                    "main_action": repo.main_action,
                    "name": repo.display_name,
                    "new": repo.data.new,
                    "pending_upgrade": repo.pending_update,
                    "releases": repo.data.published_tags,
                    "selected_tag": repo.data.selected_tag,
                    "stars": repo.data.stargazers_count,
                    "state": repo.state,
                    "status_description": repo.display_status_description,
                    "status": repo.display_status,
                    "topics": repo.data.topics,
                    "updated_info": repo.status.updated_info,
                    "version_or_commit": repo.display_version_or_commit,
                }
                for repo in hacs.repositories.list_all
                if repo.data.category in (msg.get("categories") or hacs.common.categories)
                and not repo.ignored_by_country_configuration
            ],
        )
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/repository/data",
        vol.Optional("action"): cv.string,
        vol.Optional("repository"): cv.string,
        vol.Optional("data"): cv.string,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_repository_data(hass, connection, msg):
    """Handle get media player cover command."""
    hacs: HacsBase = hass.data.get(DOMAIN)
    repo_id = msg.get("repository")
    action = msg.get("action")
    data = msg.get("data")

    if repo_id is None:
        return

    if action == "add":
        repo_id = regex.extract_repository_from_url(repo_id)
        if repo_id is None:
            return

        if repo_id in hacs.common.skip:
            hacs.common.skip.remove(repo_id)

        if hacs.common.renamed_repositories.get(repo_id):
            repo_id = hacs.common.renamed_repositories[repo_id]

        if not hacs.repositories.get_by_full_name(repo_id):
            try:
                registration = await hacs.async_register_repository(
                    repository_full_name=repo_id, category=data.lower()
                )
                if registration is not None:
                    raise HacsException(registration)
            except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
                hass.bus.async_fire(
                    "hacs/error",
                    {
                        "action": "add_repository",
                        "exception": str(sys.exc_info()[0].__name__),
                        "message": str(exception),
                    },
                )
        else:
            hass.bus.async_fire(
                "hacs/error",
                {
                    "action": "add_repository",
                    "message": f"Repository '{repo_id}' exists in the store.",
                },
            )

        repository = hacs.repositories.get_by_full_name(repo_id)
    else:
        repository = hacs.repositories.get_by_id(repo_id)

    if repository is None:
        hass.bus.async_fire("hacs/repository", {})
        return

    hacs.log.debug("Running %s for %s", action, repository.data.full_name)
    try:
        if action == "set_state":
            repository.state = data

        elif action == "set_version":
            repository.data.selected_tag = data
            await repository.update_repository(force=True)

            repository.state = None

        elif action == "install":
            was_installed = repository.data.installed
            repository.data.selected_tag = data
            await repository.update_repository(force=True)
            await repository.async_install()
            repository.state = None
            if not was_installed:
                hass.bus.async_fire("hacs/reload", {"force": True})
                await hacs.async_recreate_entities()

        elif action == "add":
            repository.state = None

        else:
            repository.state = None
            hacs.log.error("WS action '%s' is not valid", action)

        message = None
    except AIOGitHubAPIException as exception:
        message = exception
    except AttributeError as exception:
        message = f"Could not use repository with ID {repo_id} ({exception})"
    except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
        message = exception

    if message is not None:
        hacs.log.error(message)
        hass.bus.async_fire("hacs/error", {"message": str(message)})

    await hacs.data.async_write()
    connection.send_message(websocket_api.result_message(msg["id"], {}))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/repository",
        vol.Optional("action"): cv.string,
        vol.Optional("repository"): cv.string,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_repository(hass, connection, msg):
    """Handle get media player cover command."""
    hacs: HacsBase = hass.data.get(DOMAIN)
    data = {}
    repository = None

    repo_id = msg.get("repository")
    action = msg.get("action")
    if repo_id is None or action is None:
        return

    try:
        repository = hacs.repositories.get_by_id(repo_id)
        hacs.log.debug(f"Running {action} for {repository.data.full_name}")

        if action == "update":
            await repository.update_repository(ignore_issues=True, force=True)
            repository.status.updated_info = True

        elif action == "install":
            repository.data.new = False
            was_installed = repository.data.installed
            await repository.async_install()
            if not was_installed:
                hass.bus.async_fire("hacs/reload", {"force": True})
                await hacs.async_recreate_entities()

        elif action == "not_new":
            repository.data.new = False

        elif action == "uninstall":
            repository.data.new = False
            await repository.update_repository(ignore_issues=True, force=True)
            await repository.uninstall()

        elif action == "hide":
            repository.data.hide = True

        elif action == "unhide":
            repository.data.hide = False

        elif action == "show_beta":
            repository.data.show_beta = True
            await repository.update_repository(force=True)

        elif action == "hide_beta":
            repository.data.show_beta = False
            await repository.update_repository(force=True)

        elif action == "toggle_beta":
            repository.data.show_beta = not repository.data.show_beta
            await repository.update_repository(force=True)

        elif action == "delete":
            repository.data.show_beta = False
            repository.remove()

        elif action == "release_notes":
            data = [
                {
                    "name": x.name,
                    "body": x.body,
                    "tag": x.tag_name,
                }
                for x in repository.releases.objects
            ]

        elif action == "set_version":
            if msg["version"] == repository.data.default_branch:
                repository.data.selected_tag = None
            else:
                repository.data.selected_tag = msg["version"]
            await repository.update_repository(force=True)

            hass.bus.async_fire("hacs/reload", {"force": True})

        else:
            hacs.log.error(f"WS action '{action}' is not valid")

        await hacs.data.async_write()
        message = None
    except AIOGitHubAPIException as exception:
        message = exception
    except AttributeError as exception:
        message = f"Could not use repository with ID {repo_id} ({exception})"
    except BaseException as exception:  # lgtm [py/catch-base-exception] pylint: disable=broad-except
        message = exception

    if message is not None:
        hacs.log.error(message)
        hass.bus.async_fire("hacs/error", {"message": str(message)})

    if repository:
        repository.state = None
        connection.send_message(websocket_api.result_message(msg["id"], data))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/settings",
        vol.Optional("action"): cv.string,
        vol.Optional("categories"): cv.ensure_list,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_settings(hass, connection, msg):
    """Handle get media player cover command."""
    hacs: HacsBase = hass.data.get(DOMAIN)

    action = msg["action"]
    hacs.log.debug("WS action '%s'", action)

    if action == "set_fe_grid":
        hacs.configuration.frontend_mode = "Grid"

    elif action == "onboarding_done":
        hacs.configuration.onboarding_done = True

    elif action == "set_fe_table":
        hacs.configuration.frontend_mode = "Table"

    elif action == "set_fe_compact_true":
        hacs.configuration.frontend_compact = False

    elif action == "set_fe_compact_false":
        hacs.configuration.frontend_compact = True

    elif action == "clear_new":
        for repo in hacs.repositories.list_all:
            if repo.data.new and repo.data.category in msg.get("categories", []):
                hacs.log.debug(
                    "Clearing new flag from '%s'",
                    repo.data.full_name,
                )
                repo.data.new = False
    else:
        hacs.log.error("WS action '%s' is not valid", action)
    hass.bus.async_fire("hacs/config", {})
    await hacs.data.async_write()
    connection.send_message(websocket_api.result_message(msg["id"], {}))


@websocket_api.websocket_command({vol.Required("type"): "hacs/status"})
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_status(hass, connection, msg):
    """Handle get media player cover command."""
    hacs: HacsBase = hass.data.get(DOMAIN)
    connection.send_message(
        websocket_api.result_message(
            msg["id"],
            {
                "startup": hacs.status.startup,
                "background_task": False,
                "lovelace_mode": hacs.core.lovelace_mode,
                "reloading_data": hacs.status.reloading_data,
                "upgrading_all": hacs.status.upgrading_all,
                "disabled": hacs.system.disabled,
                "disabled_reason": hacs.system.disabled_reason,
                "has_pending_tasks": hacs.queue.has_pending_tasks,
                "stage": hacs.stage,
            },
        )
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/repository/ignore",
        vol.Required("repository"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def hacs_repository_ignore(hass, connection, msg):
    """Ignore a repository."""
    hacs: HacsBase = hass.data.get(DOMAIN)
    hacs.common.ignored_repositories.append(msg["repository"])
    connection.send_message(websocket_api.result_message(msg["id"]))
