"""API Endpoins."""
from aiohttp import web
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
        self.url = self.hacsapi + "/{endpoint}"

    async def post(self, request, endpoint):  # pylint: disable=unused-argument
        """Handle HACS API requests."""
        self.endpoint = endpoint
        self.postdata = await request.post()
        self.raw_headers = request.raw_headers
        self.request = request
        self.logger.debug("Endpoint ({}) called".format(endpoint), "api")
        if self.config.dev:
            self.logger.debug("Raw headers ({})".format(self.raw_headers), "api")
            self.logger.debug("Postdata ({})".format(self.postdata), "api")
        if self.endpoint in APIRESPONSE:
            response = APIRESPONSE[self.endpoint]
            response = await response.response(self)
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
        return web.json_response({"task": self.store.task_running})


@apiresponse
class Generic(HacsAPI):
    """Generic API response."""
    name = "generic"
    async def response(self):
        """Response."""
        self.logger.error("Unknown endpoint '{}'".format(self.endpoint), "adminapi")
        return web.HTTPFound("/hacsweb/{}/settings".format(self.token))


@apiresponse
class RemoveNewFlag(HacsAPI):
    """Remove new flag on all repositories."""
    name = "remove_new_flag"
    async def response(self):
        """Response."""
        for repository in self.store.repositories:
            repository = self.store.repositories[repository]
            repository.new = False
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/settings".format(self.token))


@apiresponse
class DevView(HacsAPI):
    """Set HA version view."""
    name = "devview"
    async def response(self):
        """Response."""
        render = self.render('settings/dev/{}'.format(self.postdata["view"]))
        return web.Response(body=render, content_type="text/html", charset="utf-8")

@apiresponse
class SetHAVersionAction(HacsAPI):
    """Set HA version action."""
    name = "set_ha_version_action"
    async def response(self):
        """Response."""
        self.store.ha_version = self.postdata["ha_version"]
        render = self.render('settings/dev/set_ha_version')
        return web.Response(body=render, content_type="text/html", charset="utf-8")

@apiresponse
class RepositoryInstall(HacsAPI):
    """Install repository."""
    name = "repository_install"
    async def response(self):
        """Response."""
        repository = self.store.repositories[self.postdata["repository_id"]]
        await repository.install()
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/repository/{}".format(self.token, repository.repository_id))


@apiresponse
class RepositoryUpdate(HacsAPI):
    """Update repository."""
    name = "repository_update"
    async def response(self):
        """Response."""
        repository = self.store.repositories[self.postdata["repository_id"]]
        await repository.update()
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/repository/{}".format(self.token, repository.repository_id))


@apiresponse
class RepositoryUninstall(HacsAPI):
    """Uninstall repository."""
    name = "repository_uninstall"
    async def response(self):
        """Response."""
        repository = self.store.repositories[self.postdata["repository_id"]]
        await repository.uninstall()
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/store".format(self.token))


@apiresponse
class RepositoryRemove(HacsAPI):
    """Remove repository."""
    name = "repository_remove"
    async def response(self):
        """Response."""
        repository = self.store.repositories[self.postdata["repository_id"]]
        await repository.remove()
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/settings".format(self.token))


@apiresponse
class RepositoryHide(HacsAPI):
    """Hide repository."""
    name = "repository_hide"
    async def response(self):
        """Response."""
        repository = self.store.repositories[self.postdata["repository_id"]]
        repository.hide = True
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/store".format(self.token))


@apiresponse
class RepositoryUnhide(HacsAPI):
    """Unhide repository."""
    name = "repository_unhide"
    async def response(self):
        """Response."""
        repository = self.store.repositories[self.postdata["repository_id"]]
        repository.hide = False
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/settings".format(self.token))


@apiresponse
class RepositoryBetaHide(HacsAPI):
    """Hide Beta repository."""
    name = "repository_beta_hide"
    async def response(self):
        """Response."""
        repository = self.store.repositories[self.postdata["repository_id"]]
        repository.show_beta = False
        await repository.update()
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/repository/{}".format(self.token, repository.repository_id))


@apiresponse
class RepositoryBetaShow(HacsAPI):
    """Show Beta repository."""
    name = "repository_beta_show"
    async def response(self):
        """Response."""
        repository = self.store.repositories[self.postdata["repository_id"]]
        repository.show_beta = True
        await repository.update()
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/repository/{}".format(self.token, repository.repository_id))


@apiresponse
class RepositoriesReload(HacsAPI):
    """Reload repository data."""
    name = "repositories_reload"
    async def response(self):
        """Response."""
        self.hass.async_create_task(self.update_repositories("Run it!"))
        return web.HTTPFound("/hacsweb/{}/settings".format(self.token))


@apiresponse
class RepositoriesUpgradeAll(HacsAPI):
    """Upgrade all repositories."""
    name = "repositories_upgrade_all"
    async def response(self):
        """Response."""
        for repository in self.store.repositories:
            repository = self.store.repositories[repository]
            if repository.pending_update:
                await repository.install()
        return web.HTTPFound("/hacsweb/{}/settings".format(self.token))


@apiresponse
class RepositoryRegister(HacsAPI):
    """Register repository."""
    name = "repository_register"
    async def response(self):
        """Response."""
        repository_name = self.postdata["custom_url"]
        repository_type = self.postdata["repository_type"]

        # Stip first part if it's an URL.
        if "github" in repository_name:
            repository_name = repository_name.split("github.com/")[-1]

        # Strip whitespace
        repository_name = repository_name.split()[0]

        # If it still have content, continue.
        if repository_name != "":
            if len(repository_name.split("/")) != 2:
                message = """
                    {} is not a valid format.
                    Correct format is 'https://github.com/DEVELOPER/REPOSITORY'
                    or 'DEVELOPER/REPOSITORY'.
                    """.format(repository_name)

                return web.HTTPFound("/hacsweb/{}/settings?message={}".format(self.token, message))

            is_known_repository = await self.is_known_repository(repository_name)
            if is_known_repository:
                message = "{} is already registered, look for it in the store.".format(repository_name)
                return web.HTTPFound("/hacsweb/{}/settings?message={}".format(self.token, message))

            if repository_name in self.blacklist:
                self.blacklist.remove(repository_name)

            repository, result = await self.register_new_repository(repository_type, repository_name)

            if result:
                self.store.write()
                return web.HTTPFound("/hacsweb/{}/repository/{}".format(self.token, repository.repository_id))

        message = "Could not add {} at this time, check the log for more details.".format(repository_name)
        return web.HTTPFound("/hacsweb/{}/settings?message={}".format(self.token, message))


@apiresponse
class RepositorySelectTag(HacsAPI):
    """Select tag for Repository."""
    name = "repository_select_tag"
    async def response(self):
        """Response."""
        from .aiogithub.exceptions import AIOGitHubException
        from .hacsbase.exceptions import HacsRequirement

        repository = self.store.repositories[self.postdata["repository_id"]]
        if self.postdata["selected_tag"] == repository.last_release_tag:
            repository.selected_tag = None
        else:
            repository.selected_tag = self.postdata["selected_tag"]
        try:
            await repository.update()
        except (AIOGitHubException, HacsRequirement):
            repository.selected_tag = repository.last_release_tag
            await repository.update()
            message = "The version {} is not valid for use with HACS.".format(self.postdata["selected_tag"])
            raise web.HTTPFound("/hacsweb/{}/settings?message={}".format(self.token, message))
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/repository/{}".format(self.token, repository.repository_id))


@apiresponse
class FrontentMode(HacsAPI):
    """Set the frontend mode."""
    name = "frontend_mode"
    async def response(self):
        """Response."""
        self.store.frontend_mode = self.postdata["view_type"]
        self.store.write()
        return web.HTTPFound("/hacsweb/{}/settings".format(self.token))