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
    content["dev"] = config.dev
    content["appdaemon"] = config.appdaemon
    content["python_script"] = config.python_script
    content["theme"] = config.theme
    content["option_country"] = config.option_country

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
                "status": repo.display_status,
                "status_description": repo.display_status_description,
                "additional_info": repo.information.additional_info,
                "info": repo.information.info,
                "updated_info": repo.status.updated_info,
            }
        )

    connection.send_message(websocket_api.result_message(msg["id"], content))


@websocket_api.async_response
async def hacs_repository(hass, connection, msg):
    """Handle get media player cover command."""
    repo_id = msg["repository"]
    action = msg["action"]

    repository = Hacs().get_by_id(repo_id)

    if action == "update":
        Hacs().logger.info(f"Running update for {repository.information.full_name}")
        await repository.update_repository()
        repository.status.updated_info = True

    hacs_repositories(hass, connection, msg)
