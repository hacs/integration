"""API Handler for hacs_repositories"""
import voluptuous as vol
from homeassistant.components import websocket_api

from custom_components.hacs.share import get_hacs


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
