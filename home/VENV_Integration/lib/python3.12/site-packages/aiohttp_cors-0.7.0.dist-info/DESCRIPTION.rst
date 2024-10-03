========================
CORS support for aiohttp
========================

``aiohttp_cors`` library implements
`Cross Origin Resource Sharing (CORS) <cors_>`__
support for `aiohttp <aiohttp_>`__
asyncio-powered asynchronous HTTP server.

Jump directly to `Usage`_ part to see how to use ``aiohttp_cors``.

Same-origin policy
==================

Web security model is tightly connected to
`Same-origin policy (SOP) <sop_>`__.
In short: web pages cannot *Read* resources which origin
doesn't match origin of requested page, but can *Embed* (or *Execute*)
resources and have limited ability to *Write* resources.

Origin of a page is defined in the `Standard <cors_>`__ as tuple
``(schema, host, port)``
(there is a notable exception with Internet Explorer: it doesn't use port to
define origin, but uses it's own
`Security Zones <https://msdn.microsoft.com/en-us/library/ms537183.aspx>`__).

Can *Embed* means that resource from other origin can be embedded into
the page,
e.g. by using ``<script src="...">``, ``<img src="...">``,
``<iframe src="...">``.

Cannot *Read* means that resource from other origin *source* cannot be
obtained by page
(*source* — any information that would allow to reconstruct resource).
E.g. the page can *Embed* image with ``<img src="...">``,
but it can't get information about specific pixels, so page can't reconstruct
original image
(though some information from the other resource may still be leaked:
e.g. the page can read embedded image dimensions).

Limited ability to *Write* means, that the page can send POST requests to
other origin with limited set of ``Content-Type`` values and headers.

Restriction to *Read* resource from other origin is related to authentication
mechanism that is used by browsers:
when browser reads (downloads) resource he automatically sends all security
credentials that user previously authorized for that resource
(e.g. cookies, HTTP Basic Authentication).

For example, if *Read* would be allowed and user is authenticated
in some internet banking,
malicious page would be able to embed internet banking page with ``iframe``
(since authentication is done by the browser it may be embedded as if
user is directly navigated to internet banking page),
then read user private information by reading *source* of the embedded page
(which may be not only source code, but, for example,
screenshot of the embedded internet banking page).

Cross-origin resource sharing
=============================

`Cross-origin Resource Sharing (CORS) <cors_>`__ allows to override
SOP for specific resources.

In short, CORS works in the following way.

When page ``https://client.example.com`` request (*Read*) resource
``https://server.example.com/resource`` that have other origin,
browser implicitly appends ``Origin: https://client.example.com`` header
to the HTTP request,
effectively requesting server to give read permission for
the resource to the ``https://client.example.com`` page::

    GET /resource HTTP/1.1
    Origin: https://client.example.com
    Host: server.example.com

If server allows access from the page to the resource, it responds with
resource with ``Access-Control-Allow-Origin: https://client.example.com``
HTTP header
(optionally allowing exposing custom server headers to the page and
enabling use of the user credentials on the server resource)::

    Access-Control-Allow-Origin: https://client.example.com
    Access-Control-Allow-Credentials: true
    Access-Control-Expose-Headers: X-Server-Header

Browser checks, if server responded with proper
``Access-Control-Allow-Origin`` header and accordingly allows or denies
access for the obtained resource to the page.

CORS specification designed in a way that servers that are not aware
of CORS will not expose any additional information, except allowed by the
SOP.

To request resources with custom headers or using custom HTTP methods
(e.g. ``PUT``, ``DELETE``) that are not allowed by SOP,
CORS-enabled browser first send *preflight request* to the
resource using ``OPTIONS`` method, in which he queries access to the resource
with specific method and headers::

    OPTIONS / HTTP/1.1
    Origin: https://client.example.com
    Access-Control-Request-Method: PUT
    Access-Control-Request-Headers: X-Client-Header

CORS-enabled server responds is requested method is allowed and which of
the specified headers are allowed::

    Access-Control-Allow-Origin: https://client.example.com
    Access-Control-Allow-Credentials: true
    Access-Control-Allow-Methods: PUT
    Access-Control-Allow-Headers: X-Client-Header
    Access-Control-Max-Age: 3600

Browser checks response to preflight request, and, if actual request allowed,
does actual request.

Installation
============

You can install ``aiohttp_cors`` as a typical Python library from PyPI or
from git:

.. code-block:: bash

    $ pip install aiohttp_cors

Note that ``aiohttp_cors`` requires versions of Python >= 3.4.1 and
``aiohttp`` >= 1.1.

Usage
=====

To use ``aiohttp_cors`` you need to configure the application and
enable CORS on
`resources and routes <https://aiohttp.readthedocs.org/en/stable/web.html#resources-and-routes>`__
that you want to expose:

.. code-block:: python

    import asyncio
    from aiohttp import web
    import aiohttp_cors

    @asyncio.coroutine
    def handler(request):
        return web.Response(
            text="Hello!",
            headers={
                "X-Custom-Server-Header": "Custom data",
            })

    app = web.Application()

    # `aiohttp_cors.setup` returns `aiohttp_cors.CorsConfig` instance.
    # The `cors` instance will store CORS configuration for the
    # application.
    cors = aiohttp_cors.setup(app)

    # To enable CORS processing for specific route you need to add
    # that route to the CORS configuration object and specify its
    # CORS options.
    resource = cors.add(app.router.add_resource("/hello"))
    route = cors.add(
        resource.add_route("GET", handler), {
            "http://client.example.org": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers=("X-Custom-Server-Header",),
                allow_headers=("X-Requested-With", "Content-Type"),
                max_age=3600,
            )
        })

Each route has it's own CORS configuration passed in ``CorsConfig.add()``
method.

CORS configuration is a mapping from origins to options for that origins.

In the example above CORS is configured for the resource under path ``/hello``
and HTTP method ``GET``, and in the context of CORS:

* This resource will be available using CORS only to
  ``http://client.example.org`` origin.

* Passing of credentials to this resource will be allowed.

* The resource will expose to the client ``X-Custom-Server-Header``
  server header.

* The client will be allowed to pass ``X-Requested-With`` and
  ``Content-Type`` headers to the server.

* Preflight requests will be allowed to be cached by client for ``3600``
  seconds.

Resource will be available only to the explicitly specified origins.
You can specify "all other origins" using special ``*`` origin:

.. code-block:: python

    cors.add(route, {
            "*":
                aiohttp_cors.ResourceOptions(allow_credentials=False),
            "http://client.example.org":
                aiohttp_cors.ResourceOptions(allow_credentials=True),
        })

Here the resource specified by ``route`` will be available to all origins with
disallowed credentials passing, and with allowed credentials passing only to
``http://client.example.org``.

By default ``ResourceOptions`` will be constructed without any allowed CORS
options.
This means, that resource will be available using CORS to specified origin,
but client will not be allowed to send either credentials,
or send non-simple headers, or read from server non-simple headers.

To enable sending or receiving all headers you can specify special value
``*`` instead of sequence of headers:

.. code-block:: python

    cors.add(route, {
            "http://client.example.org":
                aiohttp_cors.ResourceOptions(
                    expose_headers="*",
                    allow_headers="*"),
        })

You can specify default CORS-enabled resource options using
``aiohttp_cors.setup()``'s ``defaults`` argument:

.. code-block:: python

    cors = aiohttp_cors.setup(app, defaults={
            # Allow all to read all CORS-enabled resources from
            # http://client.example.org.
            "http://client.example.org": aiohttp_cors.ResourceOptions(),
        })

    # Enable CORS on routes.

    # According to defaults POST and PUT will be available only to
    # "http://client.example.org".
    hello_resource = cors.add(app.router.add_resource("/hello"))
    cors.add(hello_resource.add_route("POST", handler_post))
    cors.add(hello_resource.add_route("PUT", handler_put))

    # In addition to "http://client.example.org", GET request will be
    # allowed from "http://other-client.example.org" origin.
    cors.add(hello_resource.add_route("GET", handler), {
            "http://other-client.example.org":
                aiohttp_cors.ResourceOptions(),
        })

    # CORS will be enabled only on the resources added to `CorsConfig`,
    # so following resource will be NOT CORS-enabled.
    app.router.add_route("GET", "/private", handler)

Also you can specify default options for resources:

.. code-block:: python

    # Allow POST and PUT requests from "http://client.example.org" origin.
    hello_resource = cors.add(app.router.add_resource("/hello"), {
            "http://client.example.org": aiohttp_cors.ResourceOptions(),
        })
    cors.add(hello_resource.add_route("POST", handler_post))
    cors.add(hello_resource.add_route("PUT", handler_put))

Resource CORS configuration allows to use ``allow_methods`` option that
explicitly specifies list of allowed HTTP methods for origin
(or ``*`` for all HTTP methods).
By using this option it is not required to add all resource routes to
CORS configuration object:

.. code-block:: python

    # Allow POST and PUT requests from "http://client.example.org" origin.
    hello_resource = cors.add(app.router.add_resource("/hello"), {
            "http://client.example.org":
                aiohttp_cors.ResourceOptions(allow_methods=["POST", "PUT"]),
        })
    # No need to add POST and PUT routes into CORS configuration object.
    hello_resource.add_route("POST", handler_post)
    hello_resource.add_route("PUT", handler_put)
    # Still you can add additional methods to CORS configuration object:
    cors.add(hello_resource.add_route("DELETE", handler_delete))

Here is an example of how to enable CORS for all origins with all CORS
features:

.. code-block:: python

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
    })

    # Add all resources to `CorsConfig`.
    resource = cors.add(app.router.add_resource("/hello"))
    cors.add(resource.add_route("GET", handler_get))
    cors.add(resource.add_route("PUT", handler_put))
    cors.add(resource.add_route("POST", handler_put))
    cors.add(resource.add_route("DELETE", handler_delete))

Old routes API is supported — you can use ``router.add_router`` and
``router.register_route`` as before, though this usage is discouraged:

.. code-block:: python

    cors.add(
        app.router.add_route("GET", "/hello", handler), {
            "http://client.example.org": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers=("X-Custom-Server-Header",),
                allow_headers=("X-Requested-With", "Content-Type"),
                max_age=3600,
            )
        })

You can enable CORS for all added routes by accessing routes list
in the router:

.. code-block:: python

    # Setup application routes.
    app.router.add_route("GET", "/hello", handler_get)
    app.router.add_route("PUT", "/hello", handler_put)
    app.router.add_route("POST", "/hello", handler_put)
    app.router.add_route("DELETE", "/hello", handler_delete)

    # Configure default CORS settings.
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
    })

    # Configure CORS on all routes.
    for route in list(app.router.routes()):
        cors.add(route)

You can also use ``CorsViewMixin`` on ``web.View``:

.. code-block:: python

    class CorsView(web.View, CorsViewMixin):

        cors_config = {
            "*": ResourceOption(
                allow_credentials=True,
                allow_headers="X-Request-ID",
            )
        }

        @asyncio.coroutine
        def get(self):
            return web.Response(text="Done")

        @custom_cors({
            "*": ResourceOption(
                allow_credentials=True,
                allow_headers="*",
            )
        })
        @asyncio.coroutine
        def post(self):
            return web.Response(text="Done")

    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
    })

    cors.add(
        app.router.add_route("*", "/resource", CorsView),
        webview=True)


Security
========

TODO: fill this

Development
===========

To setup development environment:

.. code-block:: bash

   # Clone sources repository:
   git clone https://github.com/aio-libs/aiohttp_cors.git .
   # Create and activate virtual Python environment:
   python3 -m venv env
   source env/bin/activate
   # Install requirements and aiohttp_cors into virtual environment
   pip install -r requirements-dev.txt

To run tests:

.. code-block:: bash

   tox

To run only runtime tests in current environment:

.. code-block:: bash

   py.test

To run only static code analysis checks:

.. code-block:: bash

   tox -e check

Running Selenium tests
----------------------

To run Selenium tests with Firefox web driver you need to install Firefox.

To run Selenium tests with Chromium web driver you need to:

1. Install Chrome driver. On Ubuntu 14.04 it's in ``chromium-chromedriver``
   package.

2. Either add ``chromedriver`` to PATH or set ``WEBDRIVER_CHROMEDRIVER_PATH``
   environment variable to ``chromedriver``, e.g. on Ubuntu 14.04
   ``WEBDRIVER_CHROMEDRIVER_PATH=/usr/lib/chromium-browser/chromedriver``.

Release process
---------------

To release version ``vA.B.C`` from the current version of ``master`` branch
you need to:

1. Create local branch ``vA.B.C``.
2. In ``CHANGES.rst`` set release date to today.
3. In ``aiohttp_cors/__about__.py`` change version from ``A.B.Ca0`` to
   ``A.B.C``.
4. Create pull request with ``vA.B.C`` branch, wait for all checks to
   successfully finish (Travis and Appveyor).
5. Merge pull request to master.
6. Update and checkout ``master`` branch.

7. Create and push tag for release version to GitHub:

   .. code-block:: bash

      git tag vA.B.C
      git push --tags

   Now Travis should ran tests again, and build and deploy wheel on PyPI.

   If Travis release doesn't work for some reason, use following steps
   for manual release upload.

   1. Install fresh versions of setuptools and pip.
      Install ``wheel`` for building wheels.
      Install ``twine`` for uploading to PyPI.

      .. code-block:: bash

         pip install -U pip setuptools twine wheel

   2. Configure PyPI credentials in ``~/.pypirc``.

   3. Build distribution:

      .. code-block:: bash

         rm -rf build dist; python setup.py sdist bdist_wheel

   4. Upload new release to PyPI:

      .. code-block:: bash

         twine upload dist/*

8. Edit release description on GitHub if needed.
9. Announce new release on the *aio-libs* mailing list:
   https://groups.google.com/forum/#!forum/aio-libs.

Post release steps:

1. In ``CHANGES.rst`` add template for the next release.
2. In ``aiohttp_cors/__about__.py`` change version from ``A.B.C`` to
   ``A.(B + 1).0a0``.

Bugs
====

Please report bugs, issues, feature requests, etc. on
`GitHub <https://github.com/aio-libs/aiohttp_cors/issues>`__.


License
=======

Copyright 2015 Vladimir Rutsky <vladimir@rutsky.org>.

Licensed under the
`Apache License, Version 2.0 <https://www.apache.org/licenses/LICENSE-2.0>`__,
see ``LICENSE`` file for details.

.. _cors: http://www.w3.org/TR/cors/
.. _aiohttp: https://github.com/KeepSafe/aiohttp/
.. _sop: https://en.wikipedia.org/wiki/Same-origin_policy


=========
 CHANGES
=========

0.7.0 (2018-03-05)
==================

- Make web view check implicit and type based (#159)

- Disable Python 3.4 support (#156)

- Support aiohttp 3.0+ (#155)

0.6.0 (2017-12-21)
==================

- Support aiohttp views by ``CorsViewMixin`` (#145)

0.5.3 (2017-04-21)
==================

- Fix ``typing`` being installed on Python 3.6.

0.5.2 (2017-03-28)
==================

- Fix tests compatibility with ``aiohttp`` 2.0.
  This release and release v0.5.0 should work on ``aiohttp`` 2.0.


0.5.1 (2017-03-23)
==================

- Enforce ``aiohttp`` version to be less than 2.0.
  Newer ``aiohttp`` releases will be supported in the next release.

0.5.0 (2016-11-18)
==================

- Fix compatibility with ``aiohttp`` 1.1


0.4.0 (2016-04-04)
==================

- Fixed support with new Resources objects introduced in ``aiohttp`` 0.21.0.
  Minimum supported version of ``aiohttp`` is 0.21.4 now.

- New Resources objects are supported.
  You can specify default configuration for a Resource and use
  ``allow_methods`` to explicitly list allowed methods (or ``*`` for all
  HTTP methods):

  .. code-block:: python

        # Allow POST and PUT requests from "http://client.example.org" origin.
        hello_resource = cors.add(app.router.add_resource("/hello"), {
                "http://client.example.org":
                    aiohttp_cors.ResourceOptions(
                        allow_methods=["POST", "PUT"]),
            })
        # No need to add POST and PUT routes into CORS configuration object.
        hello_resource.add_route("POST", handler_post)
        hello_resource.add_route("PUT", handler_put)
        # Still you can add additional methods to CORS configuration object:
        cors.add(hello_resource.add_route("DELETE", handler_delete))

- ``AbstractRouterAdapter`` was completely rewritten to be more Router
  agnostic.

0.3.0 (2016-02-06)
==================

- Rename ``UrlDistatcherRouterAdapter`` to ``UrlDispatcherRouterAdapter``.

- Set maximum supported ``aiohttp`` version to ``0.20.2``, see bug #30 for
  details.

0.2.0 (2015-11-30)
==================

- Move ABCs from ``aiohttp_cors.router_adapter`` to ``aiohttp_cors.abc``.

- Rename ``RouterAdapter`` to ``AbstractRouterAdapter``.

- Fix bug with configuring CORS for named routes.

0.1.0 (2015-11-05)
==================

* Initial release.


