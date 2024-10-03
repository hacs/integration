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

"""Abstract base classes.
"""

from abc import ABCMeta, abstractmethod

from aiohttp import web


__all__ = ("AbstractRouterAdapter",)


class AbstractRouterAdapter(metaclass=ABCMeta):
    """Router adapter for handling CORS configuration interface.

    `AbstractRouter` doesn't specify how HTTP requests are delivered
    to handlers, and aiohttp_cors doesn't rely on specific implementation
    details.

    In general Router can be seen as a substance that allows to setup handlers
    for specific HTTP methods and requests paths, lets call these Router's
    items routing entities.
    Generic Router is configured with set of routing entities and their
    handlers.

    This adapter assumes that its reasonable to configure CORS for same
    routing entities as used in `AbstractRouter`.
    Routing entities will be added to CorsConfig to enable CORS for them.

    For example, for aiohttp < 0.21.0 routing entity would be
    `aiohttp.web.Route` — tuple of (HTTP method, URI path).
    And CORS can be configured for each `aiohttp.web.Route`.

    In aiohttp >= 0.21.0 there are two routing entities: Resource and Route.
    You can configure CORS for Resource (which will be interpreted as default
    for all Routes on Resoures), and configure CORS for specific Route.
    """

    @abstractmethod
    def add_preflight_handler(self,
                              routing_entity,
                              handler,
                              webview: bool=False):
        """Add OPTIONS handler for all routes defined by `routing_entity`.

        Does nothing if CORS handler already handles routing entity.
        Should fail if there are conflicting user-defined OPTIONS handlers.
        """

    @abstractmethod
    def is_preflight_request(self, request: web.Request) -> bool:
        """Is `request` is a CORS preflight request."""

    @abstractmethod
    def is_cors_enabled_on_request(self, request: web.Request) -> bool:
        """Is `request` is a request for CORS-enabled resource."""

    @abstractmethod
    def set_config_for_routing_entity(self,
                                      routing_entity,
                                      config):
        """Record configuration for routing entity.

        If router implements hierarchical routing entities, stored config
        can be used in hierarchical manner too.

        Should raise if there is conflicting configuration for the routing
        entity.
        """

    @abstractmethod
    async def get_preflight_request_config(
            self,
            preflight_request: web.Request,
            origin: str,
            requested_method: str):
        """Get stored CORS configuration for specified HTTP method and origin
        that corresponds to preflight request.

        Should raise KeyError if CORS is not configured or not enabled
        for specified HTTP method.
        """

    @abstractmethod
    def get_non_preflight_request_config(self, request: web.Request):
        """Get stored CORS configuration for routing entity that handles
        specified request."""
