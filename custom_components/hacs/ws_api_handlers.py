"""WebSocket API for HACS."""
# pylint: disable=unused-argument
import os
import voluptuous as vol
from homeassistant.components import websocket_api
import homeassistant.helpers.config_validation as cv
from .hacsbase import Hacs
from .store import async_load_from_store, async_save_to_store


async def setup_ws_api(hass):
    """Set up WS API handlers."""
    websocket_api.async_register_command(hass, hacs_settings)
    websocket_api.async_register_command(hass, hacs_config)
    websocket_api.async_register_command(hass, hacs_repositories)
    websocket_api.async_register_command(hass, hacs_repository)
    websocket_api.async_register_command(hass, hacs_repository_data)
    websocket_api.async_register_command(hass, check_local_path)
    websocket_api.async_register_command(hass, hacs_status)
    websocket_api.async_register_command(hass, acknowledge_critical_repository)
    websocket_api.async_register_command(hass, get_critical_repositories)


@websocket_api.async_response
@websocket_api.websocket_command(
    {
        vol.Required("type"): "hacs/settings",
        vol.Optional("action"): cv.string,
        vol.Optional("category"): cv.string,
    }
)
async def hacs_settings(hass, connection, msg):
    """Handle get media player cover command."""
    action = msg["action"]
    Hacs().logger.debug(f"WS action '{action}'")

    if action == "set_fe_grid":
        Hacs().configuration.frontend_mode = "Grid"

    elif action == "set_fe_table":
        Hacs().configuration.frontend_mode = "Table"

    elif action == "set_fe_compact_true":
        Hacs().configuration.frontend_compact = False

    elif action == "set_fe_compact_false":
        Hacs().configuration.frontend_compact = True

    elif action == "reload_data":
        Hacs().system.status.reloading_data = True
        hass.bus.async_fire("hacs/status", {})
        await Hacs().recuring_tasks_all()
        Hacs().system.status.reloading_data = False
        hass.bus.async_fire("hacs/status", {})

    elif action == "upgrade_all":
        Hacs().system.status.upgrading_all = True
        Hacs().system.status.background_task = True
        hass.bus.async_fire("hacs/status", {})
        for repository in Hacs().repositories:
            if repository.pending_upgrade:
                repository.status.selected_tag = None
                await repository.install()
        Hacs().system.status.upgrading_all = False
        Hacs().system.status.background_task = False
        hass.bus.async_fire("hacs/status", {})
        hass.bus.async_fire("hacs/repository", {})

    elif action == "clear_new":
        for repo in Hacs().repositories:
            if msg.get("category") == repo.information.category:
                if repo.status.new:
                    Hacs().logger.debug(
                        f"Clearing new flag from '{repo.information.full_name}'"
                    )
                    repo.status.new = False
    else:
        Hacs().logger.error(f"WS action '{action}' is not valid")
    hass.bus.async_fire("hacs/config", {})
    await Hacs().data.async_write()


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/config"})
async def hacs_config(hass, connection, msg):
    """Handle get media player cover command."""
    config = Hacs().configuration

    content = {}
    content["frontend_mode"] = config.frontend_mode
    content["frontend_compact"] = config.frontend_compact
    content["version"] = Hacs().version
    content["dev"] = config.dev
    content["appdaemon"] = config.appdaemon
    content["python_script"] = config.python_script
    content["theme"] = config.theme
    content["country"] = config.country
    content["experimental"] = config.experimental
    content["categories"] = Hacs().common.categories

    connection.send_message(websocket_api.result_message(msg["id"], content))


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/status"})
async def hacs_status(hass, connection, msg):
    """Handle get media player cover command."""
    content = {
        "startup": Hacs().system.status.startup,
        "background_task": Hacs().system.status.background_task,
        "lovelace_mode": Hacs().system.lovelace_mode,
        "reloading_data": Hacs().system.status.reloading_data,
        "upgrading_all": Hacs().system.status.upgrading_all,
        "disabled": Hacs().system.disabled,
    }
    connection.send_message(websocket_api.result_message(msg["id"], content))


@websocket_api.async_response
@websocket_api.websocket_command({vol.Required("type"): "hacs/repositories"})
async def hacs_repositories(hass, connection, msg):
    """Handle get media player cover command."""
    repositories = Hacs().repositories
    content = []
    for repo in repositories:
        content.append(
            {
                "name": repo.display_name,
                "description": repo.information.description,
                "category": repo.information.category,
                "installed": repo.status.installed,
                "id": repo.information.uid,
                "can_install": repo.can_install,
                "homeassistant": repo.repository_manifest.homeassistant,
                "hide": repo.status.hide,
                "new": repo.status.new,
                "beta": repo.status.show_beta,
                "status": repo.display_status,
                "status_description": repo.display_status_description,
                "additional_info": repo.information.additional_info,
                "info": repo.information.info,
                "updated_info": repo.status.updated_info,
                "version_or_commit": repo.display_version_or_commit,
                "custom": repo.custom,
                "domain": repo.manifest.get("domain"),
                "state": repo.state,
                "installed_version": repo.display_installed_version,
                "available_version": repo.display_available_version,
                "main_action": repo.main_action,
                "pending_upgrade": repo.pending_upgrade,
                "full_name": repo.information.full_name,
                "file_name": repo.information.file_name,
                "javascript_type": repo.information.javascript_type,
                "authors": repo.information.authors,
                "local_path": repo.content.path.local,
                "topics": repo.information.topics,
                "releases": repo.releases.published_tags,
                "selected_tag": repo.status.selected_tag,
                "default_branch": repo.information.default_branch,
            }
        )

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
    repo_id = msg.get("repository")
    action = msg.get("action")

    if repo_id is None or action is None:
        return

    repository = Hacs().get_by_id(repo_id)
    Hacs().logger.info(f"Running {action} for {repository.information.full_name}")

    if action == "update":
        await repository.update_repository()
        repository.status.updated_info = True
        repository.status.new = False

    elif action == "install":
        was_installed = repository.status.installed
        await repository.install()
        if not was_installed:
            hass.bus.async_fire("hacs/reload", {"force": False})

    elif action == "uninstall":
        await repository.uninstall()
        hass.bus.async_fire("hacs/reload", {"force": False})

    elif action == "hide":
        repository.status.hide = True

    elif action == "unhide":
        repository.status.hide = False

    elif action == "show_beta":
        repository.status.show_beta = True
        await repository.update_repository()

    elif action == "hide_beta":
        repository.status.show_beta = False
        await repository.update_repository()

    elif action == "delete":
        repository.status.show_beta = False
        repository.remove()

    elif action == "set_version":
        if msg["version"] == repository.information.default_branch:
            repository.status.selected_tag = None
        else:
            repository.status.selected_tag = msg["version"]
        await repository.update_repository()

    else:
        Hacs().logger.error(f"WS action '{action}' is not valid")

    repository.state = None
    await Hacs().data.async_write()


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
    repo_id = msg.get("repository")
    action = msg.get("action")
    data = msg.get("data")

    if repo_id is None:
        return

    if action == "add":
        if "github." in repo_id:
            repo_id = repo_id.split("github.com/")[1]

        if repo_id in Hacs().common.skip:
            Hacs().common.skip.remove(repo_id)

        if not Hacs().get_by_name(repo_id):
            result = await Hacs().register_repository(repo_id, data.lower())
            if result is not None:
                result = {"message": str(result), "action": "add_repository"}
                hass.bus.async_fire("hacs/error", result)

        repository = Hacs().get_by_name(repo_id)
    else:
        repository = Hacs().get_by_id(repo_id)

    if repository is None:
        hass.bus.async_fire("hacs/repository", {})
        return

    Hacs().logger.info(f"Running {action} for {repository.information.full_name}")

    if action == "set_state":
        repository.state = data

    elif action == "set_version":
        repository.status.selected_tag = data
        await repository.update_repository()
        repository.state = None

    elif action == "add":
        repository.state = None

    else:
        repository.state = None
        Hacs().logger.error(f"WS action '{action}' is not valid")

    await Hacs().data.async_write()


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
