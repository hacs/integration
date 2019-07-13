"""Blueprint for HacsWebResponse."""
import os
from homeassistant.components.http import HomeAssistantView
from jinja2 import Environment, PackageLoader
from aiohttp import web

from .hacsbase import HacsBase
from .repositories.repositoryinformationview import RepositoryInformationView

WEBRESPONSE = {}

def webresponse(classname):
    """Decorator used to register Web Responses."""
    WEBRESPONSE[classname.endpoint] = classname
    return classname

class HacsWebResponse(HomeAssistantView, HacsBase):
    """Base View Class for HACS."""
    requires_auth = False
    name = "hacs"

    def __init__(self):
        """Initialize."""
        self.url = self.hacsweb + "/{path:.+}"
        self.endpoint = None
        self.postdata = None
        self.raw_headers = None
        self.request = None
        self.requested_file = None

    async def get(self, request, path):  # pylint: disable=unused-argument
        """Handle HACS Web requests."""
        self.endpoint = path.split("/")[0]
        self.raw_headers = request.raw_headers
        self.request = request
        self.requested_file = path.replace(self.endpoint+"/", "")
        self.logger.debug("Endpoint ({}) called".format(self.endpoint), "web")
        if self.config.dev:
            self.logger.debug("Raw headers ({})".format(self.raw_headers), "web")
            self.logger.debug("Postdata ({})".format(self.postdata), "web")
        if self.endpoint in WEBRESPONSE:
            response = WEBRESPONSE[self.endpoint]
            response = await response.response(self)
        else:
            # Return default response.
            response = await WEBRESPONSE["generic"].response(self)

        # set headers
        response.headers["Cache-Control"] = "max-age=0, must-revalidate"

        # serve the response
        return response

    def render(self, templatefile, location=None, repository=None, message=None):
        """Render a template file."""
        loader = Environment(loader=PackageLoader('custom_components.hacs.frontend'))
        template = loader.get_template(templatefile + '.html')
        return template.render({"hacs": self, "location": location, "repository": repository, "message": message})


class HacsPluginView(HacsWebResponse):
    """Serve plugins."""
    name = "hacs:plugin"

    def __init__(self):
        """Initialize."""
        self.url = r"/community_plugin/{requested_file:.+}"

    async def get(self, request, requested_file):  # pylint: disable=unused-argument
        """Serve plugins for lovelace."""
        try:
            # Strip '?' from URL
            if "?" in requested_file:
                requested_file = requested_file.split("?")[0]

            file = "{}/www/community/{}".format(self.config_dir, requested_file)

            # Serve .gz if it exist
            if os.path.exists(file + ".gz"):
                file += ".gz"

            response = None
            if os.path.exists(file):
                self.logger.debug("Serving {} from {}".format(requested_file, file))
                response = web.FileResponse(file)
                response.headers["Cache-Control"] = "max-age=0, must-revalidate"
            else:
                self.logger.debug("Tried to serve up '%s' but it does not exist", file)
                response = web.Response(status=404)

        except Exception as error:  # pylint: disable=broad-except
            self.logger.debug(
                "there was an issue trying to serve {} - {}".format(requested_file, error
            ))
            response = web.Response(status=404)

        return response

class HacsPlugin(HacsPluginView):
    """Alias for HacsPluginView."""
    def __init__(self):
        """Initialize."""
        self.url = r"/hacsplugin/{requested_file:.+}"



@webresponse
class Settings(HacsWebResponse):
    """Serve HacsSettingsView."""
    endpoint = "settings"
    async def response(self):
        """Serve HacsOverviewView."""
        render = self.render('settings')
        return web.Response(body=render, content_type="text/html", charset="utf-8")


@webresponse
class Static(HacsWebResponse):
    """Serve static files."""
    endpoint = "static"
    async def response(self):
        """Serve static files."""
        servefile = "{}/custom_components/hacs/frontend/elements/{}".format(
            self.config_dir, self.requested_file
        )
        if os.path.exists(servefile + ".gz"):
            return web.FileResponse(servefile + ".gz")
        else:
            if os.path.exists(servefile):
                return web.FileResponse(servefile)
            else:
                return web.Response(status=404)


@webresponse
class Store(HacsWebResponse):
    """Serve HacsOverviewView."""
    endpoint = "store"
    async def response(self):
        """Serve HacsStoreView."""
        render = self.render('overviews', 'store')
        return web.Response(body=render, content_type="text/html", charset="utf-8")


@webresponse
class Overview(HacsWebResponse):
    """Serve HacsOverviewView."""
    endpoint = "overview"
    async def response(self):
        """Serve HacsOverviewView."""
        render = self.render('overviews', 'overview')
        return web.Response(body=render, content_type="text/html", charset="utf-8")


@webresponse
class Repository(HacsWebResponse):
    """Serve HacsRepositoryView."""
    endpoint = "repository"
    async def response(self):
        """Serve HacsRepositoryView."""
        message = self.request.rel_url.query.get("message")
        repository = self.store.repositories[str(self.requested_file)]
        if not repository.updated_info:
            await repository.set_repository()
            await repository.update()
            repository.updated_info = True
            self.store.write()

        if repository.new:
            repository.new = False
            self.store.write()

        repository = RepositoryInformationView(repository)
        render = self.render('repository', repository=repository, message=message)
        return web.Response(body=render, content_type="text/html", charset="utf-8")
