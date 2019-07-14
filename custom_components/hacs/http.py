"""Blueprint for HacsWebResponse."""
import os
import random
import sys
import traceback
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
        self.repository_id = path.replace(self.endpoint+"/", "")
        self.logger.debug("Endpoint ({}) called".format(self.endpoint), "web")
        if self.config.dev:
            self.logger.debug("Raw headers ({})".format(self.raw_headers), "web")
            self.logger.debug("Postdata ({})".format(self.postdata), "web")
        if self.endpoint in WEBRESPONSE:
            response = WEBRESPONSE[self.endpoint]
            response = await response.response(self)
        else:
            # Return default response.
            response = await WEBRESPONSE["error"].response(self)

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
        message = self.request.rel_url.query.get("message")
        render = self.render('settings', message=message)
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
        repository = self.store.repositories[str(self.repository_id)]
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


@webresponse
class Error(HacsWebResponse):
    """Serve error page."""
    endpoint = "error"
    async def response(self):
        """Serve error page."""
        try:
            # Get last error
            ex_type, ex_value, ex_traceback = sys.exc_info()
            trace_back = traceback.extract_tb(ex_traceback)
            stack_trace = list()

            for trace in trace_back:
                stack_trace.append(
                    "File : {} , Line : {}, Func.Name : {}, Message : {}",
                    format(trace[0], trace[1], trace[2], trace[3]),
                )

            # HARD styling
            stacks = ""
            for stack in stack_trace:
                stacks += stack
            stacks = stacks.replace(
                "File :",
                "</br>---------------------------------------------------------------</br><b>File :</b>",
            )
            stacks = stacks.replace(", Line :", "</br><b>Line :</b>")
            stacks = stacks.replace(", Func.Name :", "</br><b>Func.Name :</b>")
            stacks = stacks.replace(", Message :", "</br><b>Message :</b>")[86:-1]

            if ex_type is not None:
                codeblock = """
                    <p><b>Exception type:</b> {}</p>
                    <p><b>Exception message:</b> {}</p>
                    <code class="codeblock errorview"">{}</code>
                """.format(
                    ex_type.__name__, ex_value, stacks
                )
            else:
                codeblock = ""

            # Generate content
            content = """
                <div class='container'>
                    <h2>Something is wrong...</h2>
                    <b>Error code:</b> <i>{}</i>
                    {}
                </div>
                <div class='container'>
                    <a href='{}/new/choose' class='waves-effect waves-light btn right hacsbutton'
                        target="_blank">OPEN ISSUE</a>
                </div>
                <div class='center-align' style='margin-top: 100px'>
                    <img rel="noreferrer" src='https://i.pinimg.com/originals/ec/85/67/ec856744fac64a5a9e407733f190da5a.png'>
                </div>
            """.format(
                random.choice(self.hacsconst.ERROR), codeblock, self.const.ISSUE_URL)

        except Exception as exception:
            message = "GREAT!, even the error page is broken... ({})".format(exception)
            self.logger.error(message)
            content = "<h3>" + message + "</h3>"

        return web.Response(body=self.render('error', message=content), content_type="text/html", charset="utf-8")
