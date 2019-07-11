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

    def render(self, templatefile, location=None, repository=None):
        """Render a template file."""
        loader = Environment(loader=PackageLoader('custom_components.hacs.frontend'))
        template = loader.get_template(templatefile + '.html')
        return template.render({"hacs": self, "location": location, "repository": repository})


class HacsRunningTask(HacsViewBase):
    """Return if BG task is running."""
    name = "hacs:task"
    url = "/hacs_task"
    async def get(self, request):  # pylint: disable=unused-argument
        self.hacs.store.task_running

class HacsAdminAPI(HacsViewBase):
    """Admin API."""
    name = "adminapi"

    def __init__(self):
        """Initilize."""
        self.url = self.url_path["admin-api"] + r"/{endpoint}"

    async def post(self, request, endpoint):  # pylint: disable=unused-argument
        """Serve HacsAdminAPI requests."""
        self.logger.debug("Endpoint ({}) called".format(endpoint), "admin")
        if endpoint in APIRESPONSE:
            apiaction = APIRESPONSE[endpoint]
            return await apiaction.response(HacsBase, request)
        return await APIRESPONSE["generic"].response(HacsBase, endpoint)

@apiresponse
class APIResponseGeneric(HacsBase):
    """Generic API response."""
    name = "generic"
    async def response(self, endpoint):
        """Response."""
        self.logger.error("Unknown endpoint '{}'".format(endpoint), "adminapi")
        raise web.HTTPFound(self.url_path["settings"])
