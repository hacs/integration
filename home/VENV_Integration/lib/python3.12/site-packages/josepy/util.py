"""JOSE utilities."""
import abc
import sys
import warnings
from collections.abc import Hashable, Mapping
from types import ModuleType
from typing import Any, Callable, Iterator, List, Tuple, TypeVar, Union, cast

from cryptography.hazmat.primitives.asymmetric import ec, rsa
from OpenSSL import crypto


# Deprecated. Please use built-in decorators @classmethod and abc.abstractmethod together instead.
def abstractclassmethod(func: Callable) -> classmethod:
    return classmethod(abc.abstractmethod(func))


class ComparableX509:
    """Wrapper for OpenSSL.crypto.X509** objects that supports __eq__.

    :ivar wrapped: Wrapped certificate or certificate request.
    :type wrapped: `OpenSSL.crypto.X509` or `OpenSSL.crypto.X509Req`.

    """

    def __init__(self, wrapped: Union[crypto.X509, crypto.X509Req]) -> None:
        assert isinstance(wrapped, crypto.X509) or isinstance(wrapped, crypto.X509Req)
        self.wrapped = wrapped

    def __getattr__(self, name: str) -> Any:
        return getattr(self.wrapped, name)

    def _dump(self, filetype: int = crypto.FILETYPE_ASN1) -> bytes:
        """Dumps the object into a buffer with the specified encoding.

        :param int filetype: The desired encoding. Should be one of
            `OpenSSL.crypto.FILETYPE_ASN1`,
            `OpenSSL.crypto.FILETYPE_PEM`, or
            `OpenSSL.crypto.FILETYPE_TEXT`.

        :returns: Encoded X509 object.
        :rtype: bytes

        """
        if isinstance(self.wrapped, crypto.X509):
            return crypto.dump_certificate(filetype, self.wrapped)

        # assert in __init__ makes sure this is X509Req
        return crypto.dump_certificate_request(filetype, self.wrapped)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return self._dump() == other._dump()

    def __hash__(self) -> int:
        return hash((self.__class__, self._dump()))

    def __repr__(self) -> str:
        return "<{0}({1!r})>".format(self.__class__.__name__, self.wrapped)


class ComparableKey:
    """Comparable wrapper for ``cryptography`` keys.

    See https://github.com/pyca/cryptography/issues/2122.

    """

    __hash__: Callable[[], int] = NotImplemented

    def __init__(
        self,
        wrapped: Union[
            rsa.RSAPrivateKeyWithSerialization,
            rsa.RSAPublicKeyWithSerialization,
            ec.EllipticCurvePrivateKeyWithSerialization,
            ec.EllipticCurvePublicKeyWithSerialization,
        ],
    ):
        self._wrapped = wrapped

    def __getattr__(self, name: str) -> Any:
        return getattr(self._wrapped, name)

    def __eq__(self, other: Any) -> bool:
        if (
            not isinstance(other, self.__class__)
            or self._wrapped.__class__ is not other._wrapped.__class__
        ):
            return NotImplemented
        elif hasattr(self._wrapped, "private_numbers"):
            return self.private_numbers() == other.private_numbers()
        elif hasattr(self._wrapped, "public_numbers"):
            return self.public_numbers() == other.public_numbers()
        else:
            return NotImplemented

    def __repr__(self) -> str:
        return "<{0}({1!r})>".format(self.__class__.__name__, self._wrapped)

    def public_key(self) -> "ComparableKey":
        """Get wrapped public key."""
        if isinstance(
            self._wrapped,
            (rsa.RSAPublicKeyWithSerialization, ec.EllipticCurvePublicKeyWithSerialization),
        ):
            return self

        return self.__class__(self._wrapped.public_key())


class ComparableRSAKey(ComparableKey):
    """Wrapper for ``cryptography`` RSA keys.

    Wraps around:

    - :class:`~cryptography.hazmat.primitives.asymmetric.rsa.RSAPrivateKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.rsa.RSAPublicKey`

    """

    def __hash__(self) -> int:
        # public_numbers() hasn't got stable hash!
        # https://github.com/pyca/cryptography/issues/2143
        if isinstance(self._wrapped, rsa.RSAPrivateKeyWithSerialization):
            priv = self.private_numbers()
            pub = priv.public_numbers
            return hash(
                (self.__class__, priv.p, priv.q, priv.dmp1, priv.dmq1, priv.iqmp, pub.n, pub.e)
            )
        elif isinstance(self._wrapped, rsa.RSAPublicKeyWithSerialization):
            pub = self.public_numbers()
            return hash((self.__class__, pub.n, pub.e))

        raise NotImplementedError()


class ComparableECKey(ComparableKey):
    """Wrapper for ``cryptography`` EC keys.
    Wraps around:
    - :class:`~cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePrivateKey`
    - :class:`~cryptography.hazmat.primitives.asymmetric.ec.EllipticCurvePublicKey`
    """

    def __hash__(self) -> int:
        # public_numbers() hasn't got stable hash!
        # https://github.com/pyca/cryptography/issues/2143
        if isinstance(self._wrapped, ec.EllipticCurvePrivateKeyWithSerialization):
            priv = self.private_numbers()
            pub = priv.public_numbers
            return hash((self.__class__, pub.curve.name, pub.x, pub.y, priv.private_value))
        elif isinstance(self._wrapped, ec.EllipticCurvePublicKeyWithSerialization):
            pub = self.public_numbers()
            return hash((self.__class__, pub.curve.name, pub.x, pub.y))

        raise NotImplementedError()


GenericImmutableMap = TypeVar("GenericImmutableMap", bound="ImmutableMap")


class ImmutableMap(Mapping, Hashable):
    """Immutable key to value mapping with attribute access."""

    __slots__: Tuple[str, ...] = ()
    """Must be overridden in subclasses."""

    def __init__(self, **kwargs: Any) -> None:
        if set(kwargs) != set(self.__slots__):
            raise TypeError(
                "__init__() takes exactly the following arguments: {0} "
                "({1} given)".format(
                    ", ".join(self.__slots__), ", ".join(kwargs) if kwargs else "none"
                )
            )
        for slot in self.__slots__:
            object.__setattr__(self, slot, kwargs.pop(slot))

    def update(self: GenericImmutableMap, **kwargs: Any) -> GenericImmutableMap:
        """Return updated map."""
        items: Mapping[str, Any] = {**self, **kwargs}
        return type(self)(**items)

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError:
            raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self.__slots__)

    def __len__(self) -> int:
        return len(self.__slots__)

    def __hash__(self) -> int:
        return hash(tuple(getattr(self, slot) for slot in self.__slots__))

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("can't set attribute")

    def __repr__(self) -> str:
        return "{0}({1})".format(
            self.__class__.__name__,
            ", ".join("{0}={1!r}".format(key, value) for key, value in self.items()),
        )


class frozendict(Mapping, Hashable):
    """Frozen dictionary."""

    __slots__ = ("_items", "_keys")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        items: Mapping
        if kwargs and not args:
            items = dict(kwargs)
        elif len(args) == 1 and isinstance(args[0], Mapping):
            items = args[0]
        else:
            raise TypeError()
        # TODO: support generators/iterators

        object.__setattr__(self, "_items", items)
        object.__setattr__(self, "_keys", tuple(sorted(items.keys())))

    def __getitem__(self, key: str) -> Any:
        return self._items[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._items)

    def _sorted_items(self) -> Tuple[Tuple[str, Any], ...]:
        return tuple((key, self[key]) for key in self._keys)

    def __hash__(self) -> int:
        return hash(self._sorted_items())

    def __getattr__(self, name: str) -> Any:
        try:
            return self._items[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("can't set attribute")

    def __repr__(self) -> str:
        return "frozendict({0})".format(
            ", ".join("{0}={1!r}".format(key, value) for key, value in self._sorted_items())
        )


# This class takes a similar approach to the cryptography project to deprecate attributes
# in public modules. See the _ModuleWithDeprecation class here:
# https://github.com/pyca/cryptography/blob/91105952739442a74582d3e62b3d2111365b0dc7/src/cryptography/utils.py#L129
class _UtilDeprecationModule:
    """
    Internal class delegating to a module, and displaying warnings when attributes
    related to the deprecated "abstractclassmethod" attributes in the josepy.util module.
    """

    def __init__(self, module: ModuleType) -> None:
        self.__dict__["_module"] = module

    def __getattr__(self, attr: str) -> Any:
        if attr == "abstractclassmethod":
            warnings.warn(
                "The abstractclassmethod attribute in josepy.util is deprecated and will "
                "be removed soon. Please use the built-in decorators @classmethod and "
                "@abc.abstractmethod together instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return getattr(self._module, attr)

    def __setattr__(self, attr: str, value: Any) -> None:  # pragma: no cover
        setattr(self._module, attr, value)

    def __delattr__(self, attr: str) -> None:  # pragma: no cover
        delattr(self._module, attr)

    def __dir__(self) -> List[str]:  # pragma: no cover
        return ["_module"] + dir(self._module)


# Patching ourselves to warn about deprecation and planned removal of some elements in the module.
sys.modules[__name__] = cast(ModuleType, _UtilDeprecationModule(sys.modules[__name__]))
