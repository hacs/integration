# Copyright 2015 Vladimir Rutsky <vladimir@rutsky.org>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""CORS configuration container class definition.
"""

import collections
import warnings
from typing import Mapping, Union, Any

from aiohttp import hdrs, web

from .urldispatcher_router_adapter import ResourcesUrlDispatcherRouterAdapter
from .abc import AbstractRouterAdapter
from .resource_options import ResourceOptions
from .preflight_handler import _PreflightHandler

__all__ = (
    "CorsConfig",
)

# Positive response to Access-Control-Allow-Credentials
_TRUE = "true"
# CORS simple response headers:
# <http://www.w3.org/TR/cors/#simple-response-header>
_SIMPLE_RESPONSE_HEADERS = frozenset([
    hdrs.CACHE_CONTROL,
    hdrs.CONTENT_LANGUAGE,
    hdrs.CONTENT_TYPE,
    hdrs.EXPIRES,
    hdrs.LAST_MODIFIED,
    hdrs.PRAGMA
])


def _parse_config_options(
        config: Mapping[str, Union[ResourceOptions, Mapping[str, Any]]]=None):
    """Parse CORS configuration (default or per-route)

    :param config:
        Mapping from Origin to Resource configuration (allowed headers etc)
        defined either as mapping or `ResourceOptions` instance.

    Raises `ValueError` if configuration is not correct.
    """

    if config is None:
        return {}

    if not isinstance(config, collections.abc.Mapping):
        raise ValueError(
            "Config must be mapping, got '{}'".format(config))

    parsed = {}

    options_keys = {
        "allow_credentials", "expose_headers", "allow_headers", "max_age"
    }

    for origin, options in config.items():
        # TODO: check that all origins are properly formatted.
        # This is not a security issue, since origin is compared as strings.
        if not isinstance(origin, str):
            raise ValueError(
                "Origin must be string, got '{}'".format(origin))

        if isinstance(options, ResourceOptions):
            resource_options = options

        else:
            if not isinstance(options, collections.abc.Mapping):
                raise ValueError(
                    "Origin options must be either "
                    "aiohttp_cors.ResourceOptions instance or mapping, "
                    "got '{}'".format(options))

            unexpected_args = frozenset(options.keys()) - options_keys
            if unexpected_args:
                raise ValueError(
                    "Unexpected keywords in resource options: {}".format(
                        # pylint: disable=bad-builtin
                        ",".join(map(str, unexpected_args))))

            resource_options = ResourceOptions(**options)

        parsed[origin] = resource_options

    return parsed


_ConfigType = Mapping[str, Union[ResourceOptions, Mapping[str, Any]]]


class _CorsConfigImpl(_PreflightHandler):

    def __init__(self,
                 app: web.Application,
                 router_adapter: AbstractRouterAdapter):
        self._app = app

        self._router_adapter = router_adapter

        # Register hook for all responses.  This hook handles CORS-related
        # headers on non-preflight requests.
        self._app.on_response_prepare.append(self._on_response_prepare)

    def add(self,
            routing_entity,
            config: _ConfigType=None):
        """Enable CORS for specific route or resource.

        If route is passed CORS is enabled for route's resource.

        :param routing_entity:
            Route or Resource for which CORS should be enabled.
        :param config:
            CORS options for the route.
        :return: `routing_entity`.
        """

        parsed_config = _parse_config_options(config)

        self._router_adapter.add_preflight_handler(
            routing_entity, self._preflight_handler)
        self._router_adapter.set_config_for_routing_entity(
            routing_entity, parsed_config)

        return routing_entity

    async def _on_response_prepare(self,
                                   request: web.Request,
                                   response: web.StreamResponse):
        """Non-preflight CORS request response processor.

        If request is done on CORS-enabled route, process request parameters
        and set appropriate CORS response headers.
        """
        if (not self._router_adapter.is_cors_enabled_on_request(request) or
                self._router_adapter.is_preflight_request(request)):
            # Either not CORS enabled route, or preflight request which is
            # handled in its own handler.
            return

        # Processing response of non-preflight CORS-enabled request.

        config = self._router_adapter.get_non_preflight_request_config(request)

        # Handle according to part 6.1 of the CORS specification.

        origin = request.headers.get(hdrs.ORIGIN)
        if origin is None:
            # Terminate CORS according to CORS 6.1.1.
            return

        options = config.get(origin, config.get("*"))
        if options is None:
            # Terminate CORS according to CORS 6.1.2.
            return

        assert hdrs.ACCESS_CONTROL_ALLOW_ORIGIN not in response.headers
        assert hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS not in response.headers
        assert hdrs.ACCESS_CONTROL_EXPOSE_HEADERS not in response.headers

        # Process according to CORS 6.1.4.
        # Set exposed headers (server headers exposed to client) before
        # setting any other headers.
        if options.expose_headers == "*":
            # Expose all headers that are set in response.
            exposed_headers = \
                frozenset(response.headers.keys()) - _SIMPLE_RESPONSE_HEADERS
            response.headers[hdrs.ACCESS_CONTROL_EXPOSE_HEADERS] = \
                ",".join(exposed_headers)

        elif options.expose_headers:
            # Expose predefined list of headers.
            response.headers[hdrs.ACCESS_CONTROL_EXPOSE_HEADERS] = \
                ",".join(options.expose_headers)

        # Process according to CORS 6.1.3.
        # Set allowed origin.
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = origin
        if options.allow_credentials:
            # Set allowed credentials.
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS] = _TRUE

    async def _get_config(self, request, origin, request_method):
        config = \
            await self._router_adapter.get_preflight_request_config(
                request, origin, request_method)
        return config


class CorsConfig:
    """CORS configuration instance.

    The instance holds default CORS parameters and per-route options specified
    in `add()` method.

    Each `aiohttp.web.Application` can have exactly one instance of this class.
    """

    def __init__(self, app: web.Application, *,
                 defaults: _ConfigType=None,
                 router_adapter: AbstractRouterAdapter=None):
        """Construct CORS configuration.

        :param app:
            Application for which CORS configuration is built.
        :param defaults:
            Default CORS settings for origins.
        :param router_adapter:
            Router adapter. Required if application uses non-default router.
        """

        self.defaults = _parse_config_options(defaults)

        self._cors_impl = None

        self._resources_router_adapter = None
        self._resources_cors_impl = None

        self._old_routes_cors_impl = None

        if router_adapter is None:
            router_adapter = \
                ResourcesUrlDispatcherRouterAdapter(app.router, self.defaults)

        self._cors_impl = _CorsConfigImpl(app, router_adapter)

    def add(self,
            routing_entity,
            config: _ConfigType = None,
            webview: bool=False):
        """Enable CORS for specific route or resource.

        If route is passed CORS is enabled for route's resource.

        :param routing_entity:
            Route or Resource for which CORS should be enabled.
        :param config:
            CORS options for the route.
        :return: `routing_entity`.
        """

        if webview:
            warnings.warn('webview argument is deprecated, '
                          'views are handled authomatically without '
                          'extra settings',
                          DeprecationWarning,
                          stacklevel=2)

        return self._cors_impl.add(routing_entity, config)
