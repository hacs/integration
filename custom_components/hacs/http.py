"""Blueprint for HacsViewBase."""
from homeassistant.components.http import HomeAssistantView
from jinja2 import Environment, PackageLoader
from aiohttp import web

from .hacsbase import HacsBase

APIRESPONSE = {}

def apiresponse(classname):
    """Decorator used to API Responses."""
    APIRESPONSE[classname.name] = classname
    return classname

class HacsViewBase(HomeAssistantView, HacsBase):
    """Base View Class for HACS."""
    requires_auth = False

    def render(self, templatefile, location=None, repository=None, message=None):
        """Render a template file."""
        loader = Environment(loader=PackageLoader('custom_components.hacs.frontend'))
        template = loader.get_template(templatefile + '.html')
        return template.render({"hacs": self, "location": location, "repository": repository, "message": message})


class HacsRunningTask(HacsViewBase):
    """Return if BG task is running."""
    name = "hacs:task"
    url = "/hacs_task"
    async def get(self, request):  # pylint: disable=unused-argument
        """Handle GET request."""
        return web.json_response({"task": self.store.task_running})

class HacsAdminAPI(HacsViewBase, HacsBase):
    """Admin API."""
    name = "adminapi"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["admin-api"] + r"/{endpoint}"
        self.postdata = None
        self.request = None
        self.endpoint = None

    async def post(self, request, endpoint):  # pylint: disable=unused-argument
        """Serve HacsAdminAPI requests."""
        self.postdata = await request.post()
        self.request = request
        self.endpoint = endpoint
        self.logger.debug("Endpoint ({}) called".format(endpoint), "admin")
        if endpoint in APIRESPONSE:
            apiaction = APIRESPONSE[endpoint]
            return await apiaction.response(self)
        return await APIRESPONSE["generic"].response(self)

@apiresponse
class Generic(HacsAdminAPI):
    """Generic API response."""
    name = "generic"
    async def response(self):
        """Response."""
        self.logger.error("Unknown endpoint '{}'".format(self.endpoint), "adminapi")
        raise web.HTTPFound(self.url_path["settings"])

@apiresponse
class RemoveNewFlag(HacsAdminAPI):
    """Remove new flag on all repositories."""
    name = "remove_new_flag"
    async def response(self):
        """Response."""
        for repository in self.store.repositories:
            repository = self.store.repositories[repository]
            repository.new = False
        self.store.write()
        raise web.HTTPFound(self.url_path["settings"])

@apiresponse
class Repositories(HacsAdminAPI):
    """List all repositories."""
    name = "repositories"
    async def response(self):
        """Response."""
        render = HacsViewBase().render('settings/repositories')
        return web.Response(body=render, content_type="text/html", charset="utf-8")

@apiresponse
class Repository(HacsAdminAPI):
    """List Repository options."""
    name = "repository"
    async def response(self):
        """Response."""
        self.logger.info(self.postdata)
        render = HacsViewBase().render('settings/repositories')
        return web.Response(body=render, content_type="text/html", charset="utf-8")
