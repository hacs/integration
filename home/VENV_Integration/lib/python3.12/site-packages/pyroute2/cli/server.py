import json

from pyroute2.cli.session import Session
from pyroute2.ndb.main import NDB

try:
    from BaseHTTPServer import BaseHTTPRequestHandler
    from BaseHTTPServer import HTTPServer as HTTPServer
except ImportError:
    from http.server import BaseHTTPRequestHandler
    from http.server import HTTPServer as HTTPServer


class ProxyEncoder(object):
    def __init__(self, wfile):
        self.wfile = wfile

    def write(self, data):
        self.wfile.write(data.encode('utf-8'))

    def flush(self):
        self.wfile.flush()


class Handler(BaseHTTPRequestHandler):
    def do_error(self, code, reason):
        self.send_error(code, reason)
        self.end_headers()

    def do_POST(self):
        #
        # sanity checks:
        #
        # * path
        if self.path != '/v1/':
            return self.do_error(404, 'url not found')
        # * content length
        if 'Content-Length' not in self.headers:
            return self.do_error(411, 'Content-Length')
        # * content type
        if 'Content-Type' not in self.headers:
            return self.do_error(400, 'Content-Type')
        #

        content_length = int(self.headers['Content-Length'])
        content_type = self.headers['Content-Type']
        data = self.rfile.read(content_length)

        if content_type == 'application/json':
            try:
                request = json.loads(data)
            except ValueError:
                return self.do_error(400, 'Incorrect JSON input')
        elif content_type == 'text/plain':
            request = {'commands': data.decode('utf-8').split(';')}
        else:
            self.do_error(400, 'Incorrect content type')

        # auth plugins
        if 'X-Auth-Mech' in self.headers:
            auth_plugin = self.server.auth_plugins.get(
                self.headers['X-Auth-Mech']
            )
            if auth_plugin is None:
                return self.do_error(501, 'Authentication mechanism not found')
            try:
                am = auth_plugin(self.headers)
            except Exception:
                return self.do_error(401, 'Authentication failed')
            ndb = self.server.ndb.auth_proxy(am)
        elif self.server.auth_strict:
            return self.do_error(401, 'Authentication required')
        else:
            ndb = self.server.ndb

        session = Session(
            ndb=ndb,
            stdout=ProxyEncoder(self.wfile),
            builtins=('ls', '.', '..', 'version'),
        )
        self.send_response(200)
        self.end_headers()
        for cmd in request['commands']:
            session.handle(cmd)


class Server(HTTPServer):
    def __init__(
        self,
        address='localhost',
        port=8080,
        sources=None,
        ndb=None,
        log=None,
        auth_strict=False,
        auth_plugins=None,
    ):
        self.sessions = {}
        self.auth_strict = auth_strict
        self.auth_plugins = auth_plugins or {}
        if ndb is not None:
            self.ndb = ndb
        else:
            self.ndb = NDB(sources=sources, log=log)
        self.ndb.config.update(
            {'show_format': 'json', 'recordset_pipe': 'true'}
        )
        HTTPServer.__init__(self, (address, port), Handler)
