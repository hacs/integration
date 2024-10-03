# F401: "imported but unused"
# fmt: off
import typing

from voluptuous import validators  # noqa: F401
from voluptuous.error import Invalid, LiteralInvalid, TypeInvalid  # noqa: F401
from voluptuous.schema_builder import DefaultFactory  # noqa: F401
from voluptuous.schema_builder import Schema, default_factory, raises  # noqa: F401

# fmt: on

__author__ = 'tusharmakkar08'


def Lower(v: str) -> str:
    """Transform a string to lower case.

    >>> s = Schema(Lower)
    >>> s('HI')
    'hi'
    """
    return str(v).lower()


def Upper(v: str) -> str:
    """Transform a string to upper case.

    >>> s = Schema(Upper)
    >>> s('hi')
    'HI'
    """
    return str(v).upper()


def Capitalize(v: str) -> str:
    """Capitalise a string.

    >>> s = Schema(Capitalize)
    >>> s('hello world')
    'Hello world'
    """
    return str(v).capitalize()


def Title(v: str) -> str:
    """Title case a string.

    >>> s = Schema(Title)
    >>> s('hello world')
    'Hello World'
    """
    return str(v).title()


def Strip(v: str) -> str:
    """Strip whitespace from a string.

    >>> s = Schema(Strip)
    >>> s('  hello world  ')
    'hello world'
    """
    return str(v).strip()


class DefaultTo(object):
    """Sets a value to default_value if none provided.

    >>> s = Schema(DefaultTo(42))
    >>> s(None)
    42
    >>> s = Schema(DefaultTo(list))
    >>> s(None)
    []
    """

    def __init__(self, default_value, msg: typing.Optional[str] = None) -> None:
        self.default_value = default_factory(default_value)
        self.msg = msg

    def __call__(self, v):
        if v is None:
            v = self.default_value()
        return v

    def __repr__(self):
        return 'DefaultTo(%s)' % (self.default_value(),)


class SetTo(object):
    """Set a value, ignoring any previous value.

    >>> s = Schema(validators.Any(int, SetTo(42)))
    >>> s(2)
    2
    >>> s("foo")
    42
    """

    def __init__(self, value) -> None:
        self.value = default_factory(value)

    def __call__(self, v):
        return self.value()

    def __repr__(self):
        return 'SetTo(%s)' % (self.value(),)


class Set(object):
    """Convert a list into a set.

    >>> s = Schema(Set())
    >>> s([]) == set([])
    True
    >>> s([1, 2]) == set([1, 2])
    True
    >>> with raises(Invalid, regex="^cannot be presented as set: "):
    ...   s([set([1, 2]), set([3, 4])])
    """

    def __init__(self, msg: typing.Optional[str] = None) -> None:
        self.msg = msg

    def __call__(self, v):
        try:
            set_v = set(v)
        except Exception as e:
            raise TypeInvalid(self.msg or 'cannot be presented as set: {0}'.format(e))
        return set_v

    def __repr__(self):
        return 'Set()'


class Literal(object):
    def __init__(self, lit) -> None:
        self.lit = lit

    def __call__(self, value, msg: typing.Optional[str] = None):
        if self.lit != value:
            raise LiteralInvalid(msg or '%s not match for %s' % (value, self.lit))
        else:
            return self.lit

    def __str__(self):
        return str(self.lit)

    def __repr__(self):
        return repr(self.lit)
