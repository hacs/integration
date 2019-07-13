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
        self.raw_headers = request.raw_headers()
        self.request = request
        self.logger.debug("Endpoint ({}) called".format(endpoint), "api")
        if self.config.dev:
            self.logger.debug("Raw headers ({})".format(self.raw_headers), "api")
            self.logger.debug("Postdata ({})".format(self.postdata), "api")
        if endpoint in APIRESPONSE:
            apiaction = APIRESPONSE[endpoint]
            return await apiaction.response(self)

        # Return default response.
        return await APIRESPONSE["generic"].response(self)


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
        raise web.HTTPFound(self.url_path["settings"])

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
        raise web.HTTPFound(self.url_path["settings"])

@apiresponse
class Repositories(HacsAPI):
    """List all repositories."""
    name = "repositories"
    async def response(self):
        """Response."""
        render = self.render('settings/repositories')
        return web.Response(body=render, content_type="text/html", charset="utf-8")

@apiresponse
class DevRepository(HacsAPI):
    """List Repository options."""
    name = "devrepository"
    async def response(self):
        """Response."""
        self.logger.info(self.postdata)
        render = self.render('settings/repositories')
        return web.Response(body=render, content_type="text/html", charset="utf-8")
