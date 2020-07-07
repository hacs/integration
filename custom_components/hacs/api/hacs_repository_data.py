"""API Handler for hacs_repository_data"""
import sys

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from aiogithubapi import AIOGitHubAPIException
from homeassistant.components import websocket_api

from custom_components.hacs.helpers.classes.exceptions import HacsException
from custom_components.hacs.helpers.functions.register_repository import (
    register_repository,
)
from custom_components.hacs.share import get_hacs
from custom_components.hacs.helpers.functions.logger import getLogger


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
    logger = getLogger("api.repository_data")
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
            except (
                Exception,
                BaseException,
            ) as exception:  # pylint: disable=broad-except
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

    logger.debug(f"Running {action} for {repository.data.full_name}")
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
            await repository.async_install()
            repository.state = None
            if not was_installed:
                hass.bus.async_fire("hacs/reload", {"force": True})

        elif action == "add":
            repository.state = None

        else:
            repository.state = None
            logger.error(f"WS action '{action}' is not valid")

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

    await hacs.data.async_write()
    connection.send_message(websocket_api.result_message(msg["id"], {}))
