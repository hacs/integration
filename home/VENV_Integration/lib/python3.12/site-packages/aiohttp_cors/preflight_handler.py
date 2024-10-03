from aiohttp import hdrs, web

# Positive response to Access-Control-Allow-Credentials
_TRUE = "true"


class _PreflightHandler:

    @staticmethod
    def _parse_request_method(request: web.Request):
        """Parse Access-Control-Request-Method header of the preflight request
        """
        method = request.headers.get(hdrs.ACCESS_CONTROL_REQUEST_METHOD)
        if method is None:
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "'Access-Control-Request-Method' header is not specified")

        # FIXME: validate method string (ABNF: method = token), if parsing
        # fails, raise HTTPForbidden.

        return method

    @staticmethod
    def _parse_request_headers(request: web.Request):
        """Parse Access-Control-Request-Headers header or the preflight request

        Returns set of headers in upper case.
        """
        headers = request.headers.get(hdrs.ACCESS_CONTROL_REQUEST_HEADERS)
        if headers is None:
            return frozenset()

        # FIXME: validate each header string, if parsing fails, raise
        # HTTPForbidden.
        # FIXME: check, that headers split and stripped correctly (according
        # to ABNF).
        headers = (h.strip(" \t").upper() for h in headers.split(","))
        # pylint: disable=bad-builtin
        return frozenset(filter(None, headers))

    async def _get_config(self, request, origin, request_method):
        raise NotImplementedError()

    async def _preflight_handler(self, request: web.Request):
        """CORS preflight request handler"""

        # Handle according to part 6.2 of the CORS specification.

        origin = request.headers.get(hdrs.ORIGIN)
        if origin is None:
            # Terminate CORS according to CORS 6.2.1.
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "origin header is not specified in the request")

        # CORS 6.2.3. Doing it out of order is not an error.
        request_method = self._parse_request_method(request)

        # CORS 6.2.5. Doing it out of order is not an error.

        try:
            config = \
                await self._get_config(request, origin, request_method)
        except KeyError:
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "request method {!r} is not allowed "
                     "for {!r} origin".format(request_method, origin))

        if not config:
            # No allowed origins for the route.
            # Terminate CORS according to CORS 6.2.1.
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "no origins are allowed")

        options = config.get(origin, config.get("*"))
        if options is None:
            # No configuration for the origin - deny.
            # Terminate CORS according to CORS 6.2.2.
            raise web.HTTPForbidden(
                text="CORS preflight request failed: "
                     "origin '{}' is not allowed".format(origin))

        # CORS 6.2.4
        request_headers = self._parse_request_headers(request)

        # CORS 6.2.6
        if options.allow_headers == "*":
            pass
        else:
            disallowed_headers = request_headers - options.allow_headers
            if disallowed_headers:
                raise web.HTTPForbidden(
                    text="CORS preflight request failed: "
                         "headers are not allowed: {}".format(
                             ", ".join(disallowed_headers)))

        # Ok, CORS actual request with specified in the preflight request
        # parameters is allowed.
        # Set appropriate headers and return 200 response.

        response = web.Response()

        # CORS 6.2.7
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_ORIGIN] = origin
        if options.allow_credentials:
            # Set allowed credentials.
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_CREDENTIALS] = _TRUE

        # CORS 6.2.8
        if options.max_age is not None:
            response.headers[hdrs.ACCESS_CONTROL_MAX_AGE] = \
                str(options.max_age)

        # CORS 6.2.9
        # TODO: more optimal for client preflight request cache would be to
        # respond with ALL allowed methods.
        response.headers[hdrs.ACCESS_CONTROL_ALLOW_METHODS] = request_method

        # CORS 6.2.10
        if request_headers:
            # Note: case of the headers in the request is changed, but this
            # shouldn't be a problem, since the headers should be compared in
            # the case-insensitive way.
            response.headers[hdrs.ACCESS_CONTROL_ALLOW_HEADERS] = \
                ",".join(request_headers)

        return response
