"""Blueprint for HacsWebResponse."""
import os
from time import time
from homeassistant.components.http import HomeAssistantView
from jinja2 import Environment, PackageLoader
from aiohttp import web

from integrationhelper import Logger

from .hacsbase import Hacs


WEBRESPONSE = {}


def webresponse(classname):
    """Decorator used to register Web Responses."""
    WEBRESPONSE[classname.endpoint] = classname
    return classname


class HacsWebResponse(HomeAssistantView, Hacs):
    """Base View Class for HACS."""

    requires_auth = False
    name = "hacs"

    def __init__(self):
        """Initialize."""
        self.logger = Logger("hacs.http")
        self.url = self.hacsweb + "/{path:.+}"
        self.endpoint = None
        self.postdata = None
        self.raw_headers = None
        self.repository_id = None
        self.request = None
        self.requested_file = None

    async def get(self, request, path):  # pylint: disable=unused-argument
        """Handle HACS Web requests."""
        if self.system.disabled:
            return web.Response(status=404)
        self.endpoint = path.split("/")[0]
        self.raw_headers = request.raw_headers
        self.request = request
        self.requested_file = path.replace(self.endpoint + "/", "")
        self.repository_id = path.replace(self.endpoint + "/", "")
        if self.endpoint != "static":
            self.logger.debug(f"Endpoint ({self.endpoint}) called")
        if self.endpoint in WEBRESPONSE:
            try:
                response = WEBRESPONSE[self.endpoint]
                response = await response.response(self)
            except Exception as exception:
                render = self.render("error", message=exception)
                return web.Response(
                    body=render, content_type="text/html", charset="utf-8"
                )
        else:
            # Return default response.
            response = await WEBRESPONSE["generic"].response(self)

        # set headers
        response.headers["Cache-Control"] = "no-cache, must-revalidate, s-max_age=0"
        response.headers["Pragma"] = "no-cache"

        # serve the response
        return response

    def render(self, templatefile, location=None, repository=None, message=None):
        """Render a template file."""
        loader = Environment(loader=PackageLoader("custom_components.hacs.frontend"))
        template = loader.get_template(templatefile + ".html")
        return template.render(
            {
                "hacs": self,
                "location": location,
                "repository": repository,
                "message": message,
                "timestamp": time(),
            }
        )


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

            file = f"{self.system.config_path}/www/community/{requested_file}"

            # Serve .gz if it exist
            if os.path.exists(file + ".gz"):
                file += ".gz"

            response = None
            if os.path.exists(file):
                self.logger.debug("Serving {} from {}".format(requested_file, file))
                response = web.FileResponse(file)
                response.headers["Cache-Control"] = "max-age=0, must-revalidate"
            else:
                self.logger.error(f"Tried to serve up '{file}' but it does not exist")
                response = web.Response(status=404)

        except Exception as error:  # pylint: disable=broad-except
            self.logger.debug(
                "there was an issue trying to serve {} - {}".format(
                    requested_file, error
                )
            )
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
        message = self.request.rel_url.query.get("message")
        render = self.render("settings", "settings", message=message)
        return web.Response(body=render, content_type="text/html", charset="utf-8")


@webresponse
class Static(HacsWebResponse):
    """Serve static files."""

    endpoint = "static"

    async def response(self):
        """Serve static files."""
        servefile = f"{self.system.config_path}/custom_components/hacs/frontend/elements/{self.requested_file}"
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
        render = self.render("overviews", "store")
        return web.Response(body=render, content_type="text/html", charset="utf-8")


@webresponse
class Overview(HacsWebResponse):
    """Serve HacsOverviewView."""

    endpoint = "overview"

    async def response(self):
        """Serve HacsOverviewView."""
        render = self.render("overviews", "overview")
        return web.Response(body=render, content_type="text/html", charset="utf-8")


@webresponse
class Repository(HacsWebResponse):
    """Serve HacsRepositoryView."""

    endpoint = "repository"

    async def response(self):
        """Serve HacsRepositoryView."""
        message = self.request.rel_url.query.get("message")
        repository = self.get_by_id(str(self.repository_id))
        if repository is None:
            self.logger.error(f"No repository found with ID {str(self.repository_id)}")
            return web.Response(status=404)

        if not repository.status.updated_info:
            await repository.update_repository()
            repository.status.updated_info = True

            self.data.write()

        if repository.status.new:
            repository.status.new = False
            self.data.write()

        render = self.render("repository", repository=repository, message=message)
        return web.Response(body=render, content_type="text/html", charset="utf-8")


@webresponse
class Error(HacsWebResponse):
    """Serve error page."""

    endpoint = "error"

    async def response(self):
        """Serve error page."""
        # Generate content
        content = """
            <div class='center-align' style='margin-top: 20px'>
                <img rel="noreferrer" src='https://i.pinimg.com/originals/ec/85/67/ec856744fac64a5a9e407733f190da5a.png'>
            </div>
        """

        return web.Response(
            body=self.render("error", message=content),
            content_type="text/html",
            charset="utf-8",
        )
