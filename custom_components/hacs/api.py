"""API Endpoins."""
from time import time
from aiohttp import web

from integrationhelper import Logger

from .http import HacsWebResponse

APIRESPONSE = {}


def apiresponse(classname):
    """Decorator used to register API Responses."""
    APIRESPONSE[classname.name] = classname
    return classname


class HacsAPI(HacsWebResponse):
    """HacsAPI class."""

    name = "hacsapi"

    def __init__(self):
        """Initialize."""
        self.logger = Logger("hacs.api")
        self.url = self.hacsapi + "/{endpoint}"

    async def post(self, request, endpoint):  # pylint: disable=unused-argument
        """Handle HACS API requests."""
        if self.system.disabled:
            return web.Response(status=404)
        self.endpoint = endpoint
        self.postdata = await request.post()
        self.raw_headers = request.raw_headers
        self.request = request
        self.logger.debug(f"Endpoint ({endpoint}) called")
        if self.configuration.dev:
            self.logger.debug(f"Raw headers ({self.raw_headers})")
            self.logger.debug(f"Postdata ({self.postdata})")
        if self.endpoint in APIRESPONSE:
            try:
                response = APIRESPONSE[self.endpoint]
                response = await response.response(self)
            except Exception as exception:
                render = self.render(f"error", message=exception)
                return web.Response(
                    body=render, content_type="text/html", charset="utf-8"
                )
        else:
            # Return default response.
            response = await APIRESPONSE["generic"].response(self)

        # set headers
        response.headers["Cache-Control"] = "max-age=0, must-revalidate"

        # serve the response
        return response


class HacsRunningTask(HacsAPI):
    """Return if BG task is running."""

    name = "hacs:task"

    def __init__(self):
        """Initialize."""
        self.url = "/hacs_task"

    async def get(self, request):  # pylint: disable=unused-argument
        """Handle GET request."""
        return web.json_response({"task": self.system.status.background_task})


@apiresponse
class Generic(HacsAPI):
    """Generic API response."""

    name = "generic"

    async def response(self):
        """Response."""
        self.logger.error(f"Unknown endpoint '{self.endpoint}'")
        return web.HTTPFound(f"/hacsweb/{self.token}/settings?timestamp={time()}")


@apiresponse
class RemoveNewFlag(HacsAPI):
    """Remove new flag on all repositories."""

    name = "remove_new_flag"

    async def response(self):
        """Response."""
        for repository in self.repositories:
            repository.status.new = False
        await self.data.async_write()
        return web.HTTPFound(
            f"/hacsweb/{self.token}/{self.postdata['return']}?timestamp={time()}"
        )


@apiresponse
class DevTemplate(HacsAPI):
    """Remove new flag on all repositories."""

    name = "dev_template"

    async def response(self):
        """Response."""
        from .handler.template import render_template

        if "set" in self.postdata:
            self.developer.template_id = self.postdata.get("repository_id")
            repository = self.get_by_id(self.developer.template_id)
            template = render_template(self.postdata.get("template", ""), repository)
            info = await self.github.render_markdown(template)
            info = info.replace("<h3>", "<h6>").replace("</h3>", "</h6>")
            info = info.replace("<h2>", "<h5>").replace("</h2>", "</h5>")
            info = info.replace("<h1>", "<h4>").replace("</h1>", "</h4>")
            info = info.replace("<code>", "<code class='codeinfo'>")
            info = info.replace(
                '<a href="http', '<a rel="noreferrer" target="_blank" href="http'
            )
            info = info.replace("<ul>", "")
            info = info.replace("</ul>", "")
            self.developer.template_content = info
        else:
            self.developer.template_content = ""
            self.developer.template_id = "Repository ID"
        render = self.render("settings/dev/template_test")
        return web.Response(body=render, content_type="text/html", charset="utf-8")


@apiresponse
class DevView(HacsAPI):
    """Set HA version view."""

    name = "devview"

    async def response(self):
        """Response."""
        render = self.render(f"settings/dev/{self.postdata['view']}")
        return web.Response(body=render, content_type="text/html", charset="utf-8")


@apiresponse
class SetHAVersionAction(HacsAPI):
    """Set HA version action."""

    name = "set_ha_version_action"

    async def response(self):
        """Response."""
        self.common.ha_version = self.postdata["ha_version"]
        render = self.render("settings/dev/set_ha_version")
        return web.Response(body=render, content_type="text/html", charset="utf-8")


@apiresponse
class RepositoryInstall(HacsAPI):
    """Install repository."""

    name = "repository_install"

    async def response(self):
        """Response."""
        repository = self.get_by_id(self.postdata["repository_id"])
        await repository.install()
        await self.data.async_write()
        return web.HTTPFound(
            f"/hacsweb/{self.token}/repository/{repository.information.uid}?timestamp={time()}"
        )


@apiresponse
class RepositoryUpdate(HacsAPI):
    """Update repository."""

    name = "repository_update"

    async def response(self):
        """Response."""
        repository = self.get_by_id(self.postdata["repository_id"])
        await repository.update_repository()
        await self.data.async_write()
        return web.HTTPFound(
            f"/hacsweb/{self.token}/repository/{repository.information.uid}?timestamp={time()}"
        )


@apiresponse
class RepositoryUninstall(HacsAPI):
    """Uninstall repository."""

    name = "repository_uninstall"

    async def response(self):
        """Response."""
        repository = self.get_by_id(self.postdata["repository_id"])
        await repository.uninstall()
        await self.data.async_write()
        return web.HTTPFound(f"/hacsweb/{self.token}/overview?timestamp={time()}")


@apiresponse
class RepositoryRemove(HacsAPI):
    """Remove repository."""

    name = "repository_remove"

    async def response(self):
        """Response."""
        repository = self.get_by_id(self.postdata["repository_id"])
        await repository.remove()
        await self.data.async_write()
        return web.HTTPFound(f"/hacsweb/{self.token}/settings?timestamp={time()}")


@apiresponse
class RepositoryHide(HacsAPI):
    """Hide repository."""

    name = "repository_hide"

    async def response(self):
        """Response."""
        repository = self.get_by_id(self.postdata["repository_id"])
        repository.hide = True
        await self.data.async_write()
        return web.HTTPFound(f"/hacsweb/{self.token}/store?timestamp={time()}")


@apiresponse
class RepositoryUnhide(HacsAPI):
    """Unhide repository."""

    name = "repository_unhide"

    async def response(self):
        """Response."""
        repository = self.get_by_id(self.postdata["repository_id"])
        repository.hide = False
        await self.data.async_write()
        return web.HTTPFound(f"/hacsweb/{self.token}/settings?timestamp={time()}")


@apiresponse
class RepositoryBetaHide(HacsAPI):
    """Hide Beta repository."""

    name = "repository_beta_hide"

    async def response(self):
        """Response."""
        repository = self.get_by_id(self.postdata["repository_id"])
        repository.status.show_beta = False
        await repository.update_repository()
        await self.data.async_write()
        return web.HTTPFound(
            f"/hacsweb/{self.token}/repository/{repository.information.uid}?timestamp={time()}"
        )


@apiresponse
class RepositoryBetaShow(HacsAPI):
    """Show Beta repository."""

    name = "repository_beta_show"

    async def response(self):
        """Response."""
        repository = self.get_by_id(self.postdata["repository_id"])
        repository.status.show_beta = True
        await repository.update_repository()
        await self.data.async_write()
        return web.HTTPFound(
            f"/hacsweb/{self.token}/repository/{repository.information.uid}?timestamp={time()}"
        )


@apiresponse
class RepositoriesReload(HacsAPI):
    """Reload repository data."""

    name = "repositories_reload"

    async def response(self):
        """Response."""
        self.hass.async_create_task(self.recuring_tasks_all())
        return web.HTTPFound(f"/hacsweb/{self.token}/settings?timestamp={time()}")


@apiresponse
class RepositoriesUpgradeAll(HacsAPI):
    """Upgrade all repositories."""

    name = "repositories_upgrade_all"

    async def response(self):
        """Response."""
        for repository in self.repositories:
            if repository.pending_upgrade:
                await repository.install()
        await self.data.async_write()
        return web.HTTPFound(f"/hacsweb/{self.token}/settings?timestamp={time()}")


@apiresponse
class RepositoryRegister(HacsAPI):
    """Register repository."""

    name = "repository_register"

    async def response(self):
        """Response."""
        repository_name = self.postdata.get("custom_url")
        repository_type = self.postdata.get("repository_type")

        # Validate data
        if not repository_name:
            message = "Repository URL is missing."
            return web.HTTPFound(
                f"/hacsweb/{self.token}/settings?timestamp={time()}&message={message}"
            )
        if repository_type is None:
            message = "Type is missing for '{}'.".format(repository_name)
            return web.HTTPFound(
                f"/hacsweb/{self.token}/settings?timestamp={time()}&message={message}"
            )

        # Stip first part if it's an URL.
        if "github" in repository_name:
            repository_name = repository_name.split("github.com/")[-1]

        # Strip whitespace
        repository_name = repository_name.split()[0]

        # If it still have content, continue.
        if repository_name != "":
            if len(repository_name.split("/")) != 2:
                message = f"""
                    {repository_name} is not a valid format.
                    Correct format is 'https://github.com/DEVELOPER/REPOSITORY'
                    or 'DEVELOPER/REPOSITORY'.
                    """

                return web.HTTPFound(
                    f"/hacsweb/{self.token}/settings?timestamp={time()}&message={message}"
                )

            is_known_repository = self.is_known(repository_name)
            if is_known_repository:
                message = f"'{repository_name}' is already registered, look for it in the store."
                return web.HTTPFound(
                    f"/hacsweb/{self.token}/settings?timestamp={time()}&message={message}"
                )

            if repository_name in self.common.blacklist:
                self.common.blacklist.remove(repository_name)

            await self.register_repository(repository_name, repository_type)

            repository = self.get_by_name(repository_name)
            if repository is not None:
                return web.HTTPFound(
                    f"/hacsweb/{self.token}/repository/{repository.information.uid}?timestamp={time()}"
                )

        message = f"""
        Could not add '{repository_name}' with type '{repository_type}' at this time.</br>
        If you used the correct type, check the log for more details."""
        return web.HTTPFound(
            f"/hacsweb/{self.token}/settings?timestamp={time()}&message={message}"
        )


@apiresponse
class RepositorySelectTag(HacsAPI):
    """Select tag for Repository."""

    name = "repository_select_tag"

    async def response(self):
        """Response."""
        from aiogithubapi import AIOGitHubException
        from .hacsbase.exceptions import HacsRequirement

        repository = self.get_by_id(self.postdata["repository_id"])
        if self.postdata["selected_tag"] == repository.releases.last_release:
            repository.status.selected_tag = None
        else:
            repository.status.selected_tag = self.postdata["selected_tag"]

        try:
            await repository.update_repository()
        except (AIOGitHubException, HacsRequirement):
            repository.status.selected_tag = repository.releases.last_release
            await repository.update_repository()
            message = "The version {} is not valid for use with HACS.".format(
                self.postdata["selected_tag"]
            )
            return web.HTTPFound(
                f"/hacsweb/{self.token}/repository/{repository.information.uid}?timestamp={time()}&message={message}"
            )
        await self.data.async_write()
        return web.HTTPFound(
            f"/hacsweb/{self.token}/repository/{repository.information.uid}?timestamp={time()}"
        )


@apiresponse
class FrontentMode(HacsAPI):
    """Set the frontend mode."""

    name = "frontend_mode"

    async def response(self):
        """Response."""
        self.configuration.frontend_mode = self.postdata["view_type"]
        await self.data.async_write()
        return web.HTTPFound(f"/hacsweb/{self.token}/settings?timestamp={time()}")
