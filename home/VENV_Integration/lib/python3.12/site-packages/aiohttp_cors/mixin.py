import collections

from .preflight_handler import _PreflightHandler


def custom_cors(config):
    def wrapper(function):
        name = "{}_cors_config".format(function.__name__)
        setattr(function, name, config)
        return function
    return wrapper


class CorsViewMixin(_PreflightHandler):
    cors_config = None

    @classmethod
    def get_request_config(cls, request, request_method):
        try:
            from . import APP_CONFIG_KEY
            cors = request.app[APP_CONFIG_KEY]
        except KeyError:
            raise ValueError("aiohttp-cors is not configured.")

        method = getattr(cls, request_method.lower(), None)

        if not method:
            raise KeyError()

        config_property_key = "{}_cors_config".format(request_method.lower())

        custom_config = getattr(method, config_property_key, None)
        if not custom_config:
            custom_config = {}

        class_config = cls.cors_config
        if not class_config:
            class_config = {}

        return collections.ChainMap(custom_config, class_config, cors.defaults)

    async def _get_config(self, request, origin, request_method):
        return self.get_request_config(request, request_method)

    async def options(self):
        response = await self._preflight_handler(self.request)
        return response
