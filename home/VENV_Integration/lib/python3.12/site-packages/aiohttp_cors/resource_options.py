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

"""Resource CORS options class definition.
"""

import numbers
import collections
import collections.abc

__all__ = ("ResourceOptions",)


def _is_proper_sequence(seq):
    """Returns is seq is sequence and not string."""
    return (isinstance(seq, collections.abc.Sequence) and
            not isinstance(seq, str))


class ResourceOptions(collections.namedtuple(
        "Base",
        ("allow_credentials", "expose_headers", "allow_headers", "max_age",
         "allow_methods"))):
    """Resource CORS options."""

    __slots__ = ()

    def __init__(self, *, allow_credentials=False, expose_headers=(),
                 allow_headers=(), max_age=None, allow_methods=None):
        """Construct resource CORS options.

        Options will be normalized.

        :param allow_credentials:
            Is passing client credentials to the resource from other origin
            is allowed.
            See <http://www.w3.org/TR/cors/#user-credentials> for
            the definition.
        :type allow_credentials: bool
            Is passing client credentials to the resource from other origin
            is allowed.

        :param expose_headers:
            Server headers that are allowed to be exposed to the client.
            Simple response headers are excluded from this set, see
            <http://www.w3.org/TR/cors/#list-of-exposed-headers>.
        :type expose_headers: sequence of strings or ``*`` string.

        :param allow_headers:
            Client headers that are allowed to be passed to the resource.
            See <http://www.w3.org/TR/cors/#list-of-headers>.
        :type allow_headers: sequence of strings or ``*`` string.

        :param max_age:
            How long the results of a preflight request can be cached in a
            preflight result cache (in seconds).
            See <http://www.w3.org/TR/cors/#http-access-control-max-age>.

        :param allow_methods:
            List of allowed methods or ``*``string. Can be used in resource or
            global defaults, but not in specific route.

            It's not required to specify all allowed methods for specific
            resource, routes that have explicit CORS configuration will be
            treated as if their methods are allowed.
        """
        super().__init__()

    def __new__(cls, *, allow_credentials=False, expose_headers=(),
                allow_headers=(), max_age=None, allow_methods=None):
        """Normalize source parameters and store them in namedtuple."""

        if not isinstance(allow_credentials, bool):
            raise ValueError(
                "'allow_credentials' must be boolean, "
                "got '{!r}'".format(allow_credentials))
        _allow_credentials = allow_credentials

        # `expose_headers` is either "*", or sequence of strings.
        if expose_headers == "*":
            _expose_headers = expose_headers
        elif not _is_proper_sequence(expose_headers):
            raise ValueError(
                "'expose_headers' must be either '*', or sequence of strings, "
                "got '{!r}'".format(expose_headers))
        elif expose_headers:
            # "Access-Control-Expose-Headers" ":" #field-name
            # TODO: Check that headers are valid.
            # TODO: Remove headers that in the _SIMPLE_RESPONSE_HEADERS set
            # according to
            # <http://www.w3.org/TR/cors/#list-of-exposed-headers>.
            _expose_headers = frozenset(expose_headers)
        else:
            # No headers exposed.
            _expose_headers = frozenset()

        # `allow_headers` is either "*", or set of headers in upper case.
        if allow_headers == "*":
            _allow_headers = allow_headers
        elif not _is_proper_sequence(allow_headers):
            raise ValueError(
                "'allow_headers' must be either '*', or sequence of strings, "
                "got '{!r}'".format(allow_headers))
        else:
            # TODO: Check that headers are valid.
            _allow_headers = frozenset(h.upper() for h in allow_headers)

        if max_age is None:
            _max_age = None
        else:
            if not isinstance(max_age, numbers.Integral) or max_age < 0:
                raise ValueError(
                    "'max_age' must be non-negative integer, "
                    "got '{!r}'".format(max_age))
            _max_age = max_age

        if allow_methods is None or allow_methods == "*":
            _allow_methods = allow_methods
        elif not _is_proper_sequence(allow_methods):
            raise ValueError(
                "'allow_methods' must be either '*', or sequence of strings, "
                "got '{!r}'".format(allow_methods))
        else:
            # TODO: Check that methods are valid.
            _allow_methods = frozenset(m.upper() for m in allow_methods)

        return super().__new__(
            cls,
            allow_credentials=_allow_credentials,
            expose_headers=_expose_headers,
            allow_headers=_allow_headers,
            max_age=_max_age,
            allow_methods=_allow_methods)

    def is_method_allowed(self, method):
        if self.allow_methods is None:
            return False

        if self.allow_methods == '*':
            return True

        return method.upper() in self.allow_methods
