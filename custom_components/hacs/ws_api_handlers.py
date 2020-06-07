"""WebSocket API for HACS."""
# pylint: disable=unused-argument
import sys
import os
import voluptuous as vol
from aiogithubapi import AIOGitHubAPIException
from homeassistant.components import websocket_api
import homeassistant.helpers.config_validation as cv
from .hacsbase.exceptions import HacsException
from .store import async_load_from_store, async_save_to_store

from custom_components.hacs.globals import get_hacs, removed_repositories
from custom_components.hacs.helpers.register_repository import register_repository


async def setup_ws_api(hass):
    """Set up WS API handlers."""
    websocket_api.async_register_command(hass, hacs_settings)
    websocket_api.async_register_command(hass, hacs_config)
    websocket_api.async_register_command(hass, hacs_repositories)
    websocket_api.async_register_command(hass, hacs_repository)
    websocket_api.async_register_command(hass, hacs_repository_data)
    websocket_api.async_register_command(hass, check_local_path)
    websocket_api.async_register_command(hass, hacs_status)
    websocket_api.async_register_command(hass, hacs_removed)
    websocket_api.async_register_command(hass, acknowledge_critical_repository)
    websocket_api.async_register_command(hass, get_critical_repositories)


@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/settings",
        vol.Optional("action"): cv.string,
        vol.Optional("categories"): cv.ensure_list,
    }
)
async def hacs_settings(hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    action = msg["action"]
    hacs.logger.debug(f"WS action '{action}'")

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

    elif action == "upgrade_all":
        hacs.system.status.upgrading_all = True
        hacs.system.status.background_task = True
        hass.bus.async_fire("hacs/status", {})
        for repository in hacs.repositories:
            if repository.pending_upgrade:
                repository.data.selected_tag = None
                await repository.install()
        hacs.system.status.upgrading_all = False
        hacs.system.status.background_task = False
        hass.bus.async_fire("hacs/status", {})
        hass.bus.async_fire("hacs/repository", {})

    elif action == "clear_new":
        for repo in hacs.repositories:
            if repo.data.new and repo.data.category in msg.get("categories", []):
                hacs.logger.debug(f"Clearing new flag from '{repo.data.full_name}'")
                repo.data.new = False
    else:
        hacs.logger.error(f"WS action '{action}' is not valid")
    hass.bus.async_fire("hacs/config", {})
    await hacs.data.async_write()
    connection.send_message(websocket_api.result_message(msg["id"], {}))


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/config"})
async def hacs_config(hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    config = hacs.configuration

    content = {}
    content["frontend_mode"] = config.frontend_mode
    content["frontend_compact"] = config.frontend_compact
    content["onboarding_done"] = config.onboarding_done
    content["version"] = hacs.version
    content["frontend_expected"] = hacs.frontend.version_expected
    content["frontend_running"] = hacs.frontend.version_running
    content["dev"] = config.dev
    content["debug"] = config.debug
    content["country"] = config.country
    content["experimental"] = config.experimental
    content["categories"] = hacs.common.categories

    connection.send_message(websocket_api.result_message(msg["id"], content))


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/status"})
async def hacs_status(hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    content = {
        "startup": hacs.system.status.startup,
        "background_task": hacs.system.status.background_task,
        "lovelace_mode": hacs.system.lovelace_mode,
        "reloading_data": hacs.system.status.reloading_data,
        "upgrading_all": hacs.system.status.upgrading_all,
        "disabled": hacs.system.disabled,
        "has_pending_tasks": hacs.queue.has_pending_tasks,
    }
    connection.send_message(websocket_api.result_message(msg["id"], content))


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/removed"})
async def hacs_removed(hass, connection, msg):
    """Get information about removed repositories."""
    content = []
    for repo in removed_repositories:
        content.append(repo.to_json())
    connection.send_message(websocket_api.result_message(msg["id"], content))


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/repositories"})
async def hacs_repositories(hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    repositories = hacs.repositories
    content = []
    for repo in repositories:
        if repo.data.category in hacs.common.categories:
            data = {
                "additional_info": repo.information.additional_info,
                "authors": repo.data.authors,
                "available_version": repo.display_available_version,
                "beta": repo.data.show_beta,
                "can_install": repo.can_install,
                "category": repo.data.category,
                "country": repo.data.country,
                "config_flow": repo.data.config_flow,
                "custom": repo.custom,
                "default_branch": repo.data.default_branch,
                "description": repo.data.description,
                "domain": repo.data.domain,
                "downloads": repo.data.downloads,
                "file_name": repo.data.file_name,
                "first_install": repo.status.first_install,
                "full_name": repo.data.full_name,
                "hide": repo.data.hide,
                "hide_default_branch": repo.data.hide_default_branch,
                "homeassistant": repo.data.homeassistant,
                "id": repo.data.id,
                "info": repo.information.info,
                "installed_version": repo.display_installed_version,
                "installed": repo.data.installed,
                "issues": repo.data.open_issues,
                "javascript_type": repo.information.javascript_type,
                "last_updated": repo.data.last_updated,
                "local_path": repo.content.path.local,
                "main_action": repo.main_action,
                "name": repo.display_name,
                "new": repo.data.new,
                "pending_upgrade": repo.pending_upgrade,
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

            content.append(data)

    connection.send_message(websocket_api.result_message(msg["id"], content))


@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/repository",
        vol.Optional("action"): cv.string,
        vol.Optional("repository"): cv.string,
    }
)
async def hacs_repository(hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    try:
        repo_id = msg.get("repository")
        action = msg.get("action")

        if repo_id is None or action is None:
            return

        repository = hacs.get_by_id(repo_id)
        hacs.logger.debug(f"Running {action} for {repository.data.full_name}")

        if action == "update":
            await repository.update_repository(True)
            repository.status.updated_info = True

        elif action == "install":
            repository.data.new = False
            was_installed = repository.data.installed
            await repository.install()
            if not was_installed:
                hass.bus.async_fire("hacs/reload", {"force": True})

        elif action == "not_new":
            repository.data.new = False

        elif action == "uninstall":
            repository.data.new = False
            await repository.uninstall()

        elif action == "hide":
            repository.data.hide = True

        elif action == "unhide":
            repository.data.hide = False

        elif action == "show_beta":
            repository.data.show_beta = True
            await repository.update_repository()

        elif action == "hide_beta":
            repository.data.show_beta = False
            await repository.update_repository()

        elif action == "toggle_beta":
            repository.data.show_beta = not repository.data.show_beta
            await repository.update_repository()

        elif action == "delete":
            repository.data.show_beta = False
            repository.remove()

        elif action == "set_version":
            if msg["version"] == repository.data.default_branch:
                repository.data.selected_tag = None
            else:
                repository.data.selected_tag = msg["version"]
            await repository.update_repository()

            hass.bus.async_fire("hacs/reload", {"force": True})

        else:
            hacs.logger.error(f"WS action '{action}' is not valid")

        await hacs.data.async_write()
        message = None
    except AIOGitHubAPIException as exception:
        message = exception
    except AttributeError as exception:
        message = f"Could not use repository with ID {repo_id} ({exception})"
    except Exception as exception:  # pylint: disable=broad-except
        message = exception

    if message is not None:
        hacs.logger.error(message)
        hass.bus.async_fire("hacs/error", {"message": str(exception)})

    repository.state = None
    connection.send_message(websocket_api.result_message(msg["id"], {}))


@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/repository/data",
        vol.Optional("action"): cv.string,
        vol.Optional("repository"): cv.string,
        vol.Optional("data"): cv.string,
    }
)
async def hacs_repository_data(hass, connection, msg):
    """Handle get media player cover command."""
    hacs = get_hacs()
    repo_id = msg.get("repository")
    action = msg.get("action")
    data = msg.get("data")

    if repo_id is None:
        return

    if action == "add":
        if "github." in repo_id:
            repo_id = repo_id.split("github.com/")[1]

        if repo_id in hacs.common.skip:
            hacs.common.skip.remove(repo_id)

        if not hacs.get_by_name(repo_id):
            try:
                registration = await register_repository(repo_id, data.lower())
                if registration is not None:
                    raise HacsException(registration)
            except Exception as exception:  # pylint: disable=broad-except
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

        repository = hacs.get_by_name(repo_id)
    else:
        repository = hacs.get_by_id(repo_id)

    if repository is None:
        hass.bus.async_fire("hacs/repository", {})
        return

    hacs.logger.debug(f"Running {action} for {repository.data.full_name}")
    try:
        if action == "set_state":
            repository.state = data

        elif action == "set_version":
            repository.data.selected_tag = data
            await repository.update_repository()

            repository.state = None

        elif action == "install":
            was_installed = repository.data.installed
            repository.data.selected_tag = data
            await repository.update_repository()
            await repository.install()
            repository.state = None
            if not was_installed:
                hass.bus.async_fire("hacs/reload", {"force": True})

        elif action == "add":
            repository.state = None

        else:
            repository.state = None
            hacs.logger.error(f"WS action '{action}' is not valid")

        message = None
    except AIOGitHubAPIException as exception:
        message = exception
    except AttributeError as exception:
        message = f"Could not use repository with ID {repo_id} ({exception})"
    except Exception as exception:  # pylint: disable=broad-except
        message = exception

    if message is not None:
        hacs.logger.error(message)
        hass.bus.async_fire("hacs/error", {"message": str(exception)})

    await hacs.data.async_write()
    connection.send_message(websocket_api.result_message(msg["id"], {}))


@websocket_api.async_response
@websocket_api.websocket_command(
    {vol.Required("type"): "hacs/check_path", vol.Optional("path"): cv.string}
)
async def check_local_path(hass, connection, msg):
    """Handle get media player cover command."""
    path = msg.get("path")
    exist = {"exist": False}

    if path is None:
        return

    if os.path.exists(path):
        exist["exist"] = True

    connection.send_message(websocket_api.result_message(msg["id"], exist))


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/get_critical"})
async def get_critical_repositories(hass, connection, msg):
    """Handle get media player cover command."""
    critical = await async_load_from_store(hass, "critical")
    if not critical:
        critical = []
    connection.send_message(websocket_api.result_message(msg["id"], critical))


@websocket_api.async_response
@websocket_api.websocket_command(
    {vol.Required("type"): "hacs/critical", vol.Optional("repository"): cv.string}
)
async def acknowledge_critical_repository(hass, connection, msg):
    """Handle get media player cover command."""
    repository = msg["repository"]

    critical = await async_load_from_store(hass, "critical")
    for repo in critical:
        if repository == repo["repository"]:
            repo["acknowledged"] = True
    await async_save_to_store(hass, "critical", critical)
    connection.send_message(websocket_api.result_message(msg["id"], critical))
