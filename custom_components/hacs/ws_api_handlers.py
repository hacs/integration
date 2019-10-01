"""WebSocket API for HACS."""
from homeassistant.components import websocket_api
from homeassistant.core import callback
from .hacsbase import Hacs


@callback
def hacs_config(hass, connection, msg):
    """Handle get media player cover command."""
    config = Hacs().configuration

    content = {}
    content["frontend_mode"] = config.frontend_mode
    content["version"] = Hacs().version
    content["dev"] = config.dev
    content["appdaemon"] = config.appdaemon
    content["python_script"] = config.python_script
    content["theme"] = config.theme
    content["option_country"] = config.option_country
    content["categories"] = Hacs().common.categories

    connection.send_message(websocket_api.result_message(msg["id"], content))


@callback
def hacs_repositories(hass, connection, msg):
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
                "hide": repo.status.hide,
                "beta": repo.status.show_beta,
                "status": repo.display_status,
                "status_description": repo.display_status_description,
                "additional_info": repo.information.additional_info,
                "info": repo.information.info,
                "updated_info": repo.status.updated_info,
                "version_or_commit": repo.display_version_or_commit,
                "custom": repo.custom,
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
async def hacs_repository(hass, connection, msg):
    """Handle get media player cover command."""
    repo_id = msg["repository"]
    action = msg["action"]

    repository = Hacs().get_by_id(repo_id)
    Hacs().logger.info(f"Running {action} for {repository.information.full_name}")

    if action == "update":
        await repository.update_repository()
        repository.status.updated_info = True
        repository.status.new = False

    elif action == "install":
        await repository.install()

    elif action == "uninstall":
        await repository.uninstall()

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

    Hacs().data.write()

    hacs_repositories(hass, connection, msg)


@websocket_api.async_response
async def hacs_repository_data(hass, connection, msg):
    """Handle get media player cover command."""
    repo_id = msg["repository"]
    action = msg["action"]
    data = msg["data"]

    if action == "add":
        if "github.com" in repo_id:
            repo_id = repo_id.split("github.com/")[1]
        await Hacs().register_repository(repo_id, data.lower())
        repository = Hacs().get_by_name(repo_id)
    else:
        repository = Hacs().get_by_id(repo_id)
    Hacs().logger.info(f"Running {action} for {repository.information.full_name}")

    if action == "set_version":
        repository.status.selected_tag = data
        await repository.update_repository()

    elif action == "add":
        pass

    else:
        Hacs().logger.error(f"WS action '{action}' is not valid")

    Hacs().data.write()

    hacs_repositories(hass, connection, msg)
