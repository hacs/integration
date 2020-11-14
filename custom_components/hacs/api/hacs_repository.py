"""API Handler for hacs_repository"""
import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiogithubapi import AIOGitHubAPIException
from homeassistant.components import websocket_api

from custom_components.hacs.helpers.functions.logger import getLogger
from custom_components.hacs.share import get_hacs


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
    logger = getLogger()
    data = {}
    repository = None

    repo_id = msg.get("repository")
    action = msg.get("action")
    if repo_id is None or action is None:
        return

    try:
        repository = hacs.get_by_id(repo_id)
        logger.debug(f"Running {action} for {repository.data.full_name}")

        if action == "update":
            await repository.update_repository(True)
            repository.status.updated_info = True

        elif action == "install":
            repository.data.new = False
            was_installed = repository.data.installed
            await repository.async_install()
            if not was_installed:
                hass.bus.async_fire("hacs/reload", {"force": True})

        elif action == "not_new":
            repository.data.new = False

        elif action == "uninstall":
            repository.data.new = False
            await repository.update_repository(True)
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

        elif action == "release_notes":
            data = [
                {
                    "name": x.attributes["name"],
                    "body": x.attributes["body"],
                    "tag": x.attributes["tag_name"],
                }
                for x in repository.releases.objects
            ]

        elif action == "set_version":
            if msg["version"] == repository.data.default_branch:
                repository.data.selected_tag = None
            else:
                repository.data.selected_tag = msg["version"]
            await repository.update_repository()

            hass.bus.async_fire("hacs/reload", {"force": True})

        else:
            logger.error(f"WS action '{action}' is not valid")

        await hacs.data.async_write()
        message = None
    except AIOGitHubAPIException as exception:
        message = exception
    except AttributeError as exception:
        message = f"Could not use repository with ID {repo_id} ({exception})"
    except (Exception, BaseException) as exception:  # pylint: disable=broad-except
        message = exception

    if message is not None:
        logger.error(message)
        hass.bus.async_fire("hacs/error", {"message": str(message)})

    if repository:
        repository.state = None
        connection.send_message(websocket_api.result_message(msg["id"], data))
