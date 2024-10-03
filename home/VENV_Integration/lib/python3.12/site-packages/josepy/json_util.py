"""JSON (de)serialization framework.

The framework presented here is somewhat based on `Go's "json" package`_
(especially the ``omitempty`` functionality).

.. _`Go's "json" package`: http://golang.org/pkg/encoding/json/

"""
import abc
import binascii
import logging
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Type,
    TypeVar,
)

from OpenSSL import crypto

from josepy import b64, errors, interfaces, util

logger = logging.getLogger(__name__)


def field(
    json_name: str,
    default: Any = None,
    omitempty: bool = False,
    decoder: Optional[Callable[[Any], Any]] = None,
    encoder: Optional[Callable[[Any], Any]] = None,
) -> Any:
    """Convenient function to declare a :class:`Field` with proper type annotations.

    This function allows to write the following code:

    import josepy
    class JSON(josepy.JSONObjectWithFields):
        typ: str = josepy.field('type')

        def other_type(self) -> str:
            return self.typ

    """
    return _TypedField(
        json_name=json_name, default=default, omitempty=omitempty, decoder=decoder, encoder=encoder
    )


class Field:
    """JSON object field.

    :class:`Field` is meant to be used together with
    :class:`JSONObjectWithFields`.

    ``encoder`` (``decoder``) is a callable that accepts a single
    parameter, i.e. a value to be encoded (decoded), and returns the
    serialized (deserialized) value. In case of errors it should raise
    :class:`~josepy.errors.SerializationError`
    (:class:`~josepy.errors.DeserializationError`).

    Note, that ``decoder`` should perform partial serialization only.

    :ivar str json_name: Name of the field when encoded to JSON.
    :ivar default: Default value (used when not present in JSON object).
    :ivar bool omitempty: If ``True`` and the field value is empty, then
        it will not be included in the serialized JSON object, and
        ``default`` will be used for deserialization. Otherwise, if ``False``,
        field is considered as required, value will always be included in the
        serialized JSON objected, and it must also be present when
        deserializing.

    """

    __slots__ = ("json_name", "default", "omitempty", "fdec", "fenc")

    def __init__(
        self,
        json_name: str,
        default: Any = None,
        omitempty: bool = False,
        decoder: Optional[Callable[[Any], Any]] = None,
        encoder: Optional[Callable[[Any], Any]] = None,
    ) -> None:
        self.json_name = json_name
        self.default = default
        self.omitempty = omitempty

        self.fdec = self.default_decoder if decoder is None else decoder
        self.fenc = self.default_encoder if encoder is None else encoder

    @classmethod
    def _empty(cls, value: Any) -> bool:
        """Is the provided value considered "empty" for this field?

        This is useful for subclasses that might want to override the
        definition of being empty, e.g. for some more exotic data types.

        """
        return not isinstance(value, bool) and not value

    def omit(self, value: Any) -> bool:
        """Omit the value in output?"""
        return self._empty(value) and self.omitempty

    def _update_params(self, **kwargs: Any) -> "Field":
        current = {
            "json_name": self.json_name,
            "default": self.default,
            "omitempty": self.omitempty,
            "decoder": self.fdec,
            "encoder": self.fenc,
            **kwargs,
        }
        return type(self)(**current)

    def decoder(self, fdec: Callable[[Any], Any]) -> "Field":
        """Descriptor to change the decoder on JSON object field."""
        return self._update_params(decoder=fdec)

    def encoder(self, fenc: Callable[[Any], Any]) -> "Field":
        """Descriptor to change the encoder on JSON object field."""
        return self._update_params(encoder=fenc)

    def decode(self, value: Any) -> Any:
        """Decode a value, optionally with context JSON object."""
        return self.fdec(value)

    def encode(self, value: Any) -> Any:
        """Encode a value, optionally with context JSON object."""
        return self.fenc(value)

    @classmethod
    def default_decoder(cls, value: Any) -> Any:
        """Default decoder.

        Recursively deserialize into immutable types (
        :class:`josepy.util.frozendict` instead of
        :func:`dict`, :func:`tuple` instead of :func:`list`).

        """
        # bases cases for different types returned by json.loads
        if isinstance(value, list):
            return tuple(cls.default_decoder(subvalue) for subvalue in value)
        elif isinstance(value, dict):
            return util.frozendict(
                {
                    cls.default_decoder(key): cls.default_decoder(value)
                    for key, value in value.items()
                }
            )
        else:  # integer or string
            return value

    @classmethod
    def default_encoder(cls, value: Any) -> Any:
        """Default (passthrough) encoder."""
        # field.to_partial_json() is no good as encoder has to do partial
        # serialization only
        return value


class _TypedField(Field):
    """Specialized class to mark a JSON object field with typed annotations.

    This class is kept private because fields are supposed to be declared
    using the :function:`field` in this situation.

    In the future the :class:`Field` may be removed in favor of this one."""


class JSONObjectWithFieldsMeta(abc.ABCMeta):
    """Metaclass for :class:`JSONObjectWithFields` and its subclasses.

    It makes sure that, for any class ``cls`` with ``__metaclass__``
    set to ``JSONObjectWithFieldsMeta``:

    1. All fields (attributes of type :class:`Field`) in the class
       definition are moved to the ``cls._fields`` dictionary, where
       keys are field attribute names and values are fields themselves.

    2. ``cls.__slots__`` is extended by all field attribute names
       (i.e. not :attr:`Field.json_name`). Original ``cls.__slots__``
       are stored in ``cls._orig_slots``.

    In a consequence, for a field attribute name ``some_field``,
    ``cls.some_field`` will be a slot descriptor and not an instance
    of :class:`Field`. For example::

      some_field = Field('someField', default=())

      class Foo:
          __metaclass__ = JSONObjectWithFieldsMeta
          __slots__ = ('baz',)
          some_field = some_field

      assert Foo.__slots__ == ('some_field', 'baz')
      assert Foo._orig_slots == ()
      assert Foo.some_field is not Field

      assert Foo._fields.keys() == ['some_field']
      assert Foo._fields['some_field'] is some_field

    As an implementation note, this metaclass inherits from
    :class:`abc.ABCMeta` (and not the usual :class:`type`) to mitigate
    the metaclass conflict (:class:`ImmutableMap` and
    :class:`JSONDeSerializable`, parents of :class:`JSONObjectWithFields`,
    use :class:`abc.ABCMeta` as its metaclass).

    """

    _fields: Dict[str, Field] = {}
    _orig_slots: Iterable[str]

    def __new__(
        mcs, name: str, bases: List[str], namespace: Dict[str, Any]
    ) -> "JSONObjectWithFieldsMeta":
        fields: Dict[str, Field] = {}

        for base in bases:
            fields.update(getattr(base, "_fields", {}))
        # Do not reorder, this class might override fields from base classes!
        # We use a copy of namespace in the loop because the loop modifies it.
        for key, value in namespace.copy().items():
            if isinstance(value, Field):
                if isinstance(value, _TypedField):
                    # Ensure the type annotation has been set for the field.
                    # Error out if it is not the case.
                    if key not in namespace.get("__annotations__", {}):
                        raise ValueError(
                            f"Field `{key}` in JSONObject `{name}` has no type annotation."
                        )
                fields[key] = namespace.pop(key)

        namespace["_orig_slots"] = namespace.get("__slots__", ())
        namespace["__slots__"] = tuple(list(namespace["_orig_slots"]) + list(fields.keys()))
        namespace["_fields"] = fields

        return abc.ABCMeta.__new__(mcs, name, bases, namespace)  # type: ignore[arg-type]


GenericJSONObjectWithFields = TypeVar("GenericJSONObjectWithFields", bound="JSONObjectWithFields")


class JSONObjectWithFields(
    util.ImmutableMap, interfaces.JSONDeSerializable, metaclass=JSONObjectWithFieldsMeta
):
    """JSON object with fields.

    Example::

      class Foo(JSONObjectWithFields):
          bar = Field('Bar')
          empty = Field('Empty', omitempty=True)

          @bar.encoder
          def bar(value):
              return value + 'bar'

          @bar.decoder
          def bar(value):
              if not value.endswith('bar'):
                  raise errors.DeserializationError('No bar suffix!')
              return value[:-3]

      assert Foo(bar='baz').to_partial_json() == {'Bar': 'bazbar'}
      assert Foo.from_json({'Bar': 'bazbar'}) == Foo(bar='baz')
      assert (Foo.from_json({'Bar': 'bazbar', 'Empty': '!'})
              == Foo(bar='baz', empty='!'))
      assert Foo(bar='baz').bar == 'baz'

    """

    @classmethod
    def _defaults(cls) -> Dict[str, Any]:
        """Get default fields values."""
        return {slot: field.default for slot, field in cls._fields.items()}

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**{**self._defaults(), **kwargs})

    def encode(self, name: str) -> Any:
        """Encode a single field.

        :param str name: Name of the field to be encoded.

        :raises errors.SerializationError: if field cannot be serialized
        :raises errors.Error: if field could not be found

        """
        try:
            field = self._fields[name]  # type: ignore[attr-defined]
        except KeyError:
            raise errors.Error("Field not found: {0}".format(name))

        return field.encode(getattr(self, name))

    def fields_to_partial_json(self) -> Dict[str, Any]:
        """Serialize fields to JSON."""
        jobj = {}
        omitted = set()
        for slot, field in self._fields.items():  # type: ignore[attr-defined]
            value = getattr(self, slot)

            if field.omit(value):
                omitted.add((slot, value))
            else:
                try:
                    jobj[field.json_name] = field.encode(value)
                except errors.SerializationError as error:
                    raise errors.SerializationError(
                        "Could not encode {0} ({1}): {2}".format(slot, value, error)
                    )
        return jobj

    def to_partial_json(self) -> Dict[str, Any]:
        return self.fields_to_partial_json()

    @classmethod
    def _check_required(cls, jobj: Mapping[str, Any]) -> None:
        missing = set()
        for _, field in cls._fields.items():
            if not field.omitempty and field.json_name not in jobj:
                missing.add(field.json_name)

        if missing:
            raise errors.DeserializationError(
                "The following fields are required: {0}".format(",".join(missing))
            )

    @classmethod
    def fields_from_json(cls, jobj: Mapping[str, Any]) -> Any:
        """Deserialize fields from JSON."""
        cls._check_required(jobj)
        fields = {}
        for slot, field in cls._fields.items():
            if field.json_name not in jobj and field.omitempty:
                fields[slot] = field.default
            else:
                value = jobj[field.json_name]
                try:
                    fields[slot] = field.decode(value)
                except errors.DeserializationError as error:
                    raise errors.DeserializationError(
                        "Could not decode {0!r} ({1!r}): {2}".format(slot, value, error)
                    )
        return fields

    @classmethod
    def from_json(
        cls: Type[GenericJSONObjectWithFields], jobj: Mapping[str, Any]
    ) -> GenericJSONObjectWithFields:
        return cls(**cls.fields_from_json(jobj))


def encode_b64jose(data: bytes) -> str:
    """Encode JOSE Base-64 field.

    :param bytes data:
    :rtype: `str`

    """
    # b64encode produces ASCII characters only
    return b64.b64encode(data).decode("ascii")


def decode_b64jose(data: str, size: Optional[int] = None, minimum: bool = False) -> bytes:
    """Decode JOSE Base-64 field.

    :param unicode data:
    :param int size: Required length (after decoding).
    :param bool minimum: If ``True``, then `size` will be treated as
        minimum required length, as opposed to exact equality.

    :rtype: bytes

    """
    try:
        decoded = b64.b64decode(data.encode())
    except binascii.Error as error:
        raise errors.DeserializationError(error)

    if size is not None and (
        (not minimum and len(decoded) != size) or (minimum and len(decoded) < size)
    ):
        raise errors.DeserializationError("Expected at least or exactly {0} bytes".format(size))

    return decoded


def encode_hex16(value: bytes) -> str:
    """Hexlify.

    :param bytes value:
    :rtype: unicode

    """
    return binascii.hexlify(value).decode()


def decode_hex16(value: str, size: Optional[int] = None, minimum: bool = False) -> bytes:
    """Decode hexlified field.

    :param unicode value:
    :param int size: Required length (after decoding).
    :param bool minimum: If ``True``, then `size` will be treated as
        minimum required length, as opposed to exact equality.

    :rtype: bytes

    """
    value_b = value.encode()
    if size is not None and (
        (not minimum and len(value_b) != size * 2) or (minimum and len(value_b) < size * 2)
    ):
        raise errors.DeserializationError()
    try:
        return binascii.unhexlify(value_b)
    except binascii.Error as error:
        raise errors.DeserializationError(error)


def encode_cert(cert: util.ComparableX509) -> str:
    """Encode certificate as JOSE Base-64 DER.

    :type cert: `OpenSSL.crypto.X509` wrapped in `.ComparableX509`
    :rtype: unicode

    """
    if isinstance(cert.wrapped, crypto.X509Req):
        raise ValueError("Error input is actually a certificate request.")

    return encode_b64jose(crypto.dump_certificate(crypto.FILETYPE_ASN1, cert.wrapped))


def decode_cert(b64der: str) -> util.ComparableX509:
    """Decode JOSE Base-64 DER-encoded certificate.

    :param unicode b64der:
    :rtype: `OpenSSL.crypto.X509` wrapped in `.ComparableX509`

    """
    try:
        return util.ComparableX509(
            crypto.load_certificate(crypto.FILETYPE_ASN1, decode_b64jose(b64der))
        )
    except crypto.Error as error:
        raise errors.DeserializationError(error)


def encode_csr(csr: util.ComparableX509) -> str:
    """Encode CSR as JOSE Base-64 DER.

    :type csr: `OpenSSL.crypto.X509Req` wrapped in `.ComparableX509`
    :rtype: unicode

    """
    if isinstance(csr.wrapped, crypto.X509):
        raise ValueError("Error input is actually a certificate.")

    return encode_b64jose(crypto.dump_certificate_request(crypto.FILETYPE_ASN1, csr.wrapped))


def decode_csr(b64der: str) -> util.ComparableX509:
    """Decode JOSE Base-64 DER-encoded CSR.

    :param unicode b64der:
    :rtype: `OpenSSL.crypto.X509Req` wrapped in `.ComparableX509`

    """
    try:
        return util.ComparableX509(
            crypto.load_certificate_request(crypto.FILETYPE_ASN1, decode_b64jose(b64der))
        )
    except crypto.Error as error:
        raise errors.DeserializationError(error)


GenericTypedJSONObjectWithFields = TypeVar(
    "GenericTypedJSONObjectWithFields", bound="TypedJSONObjectWithFields"
)


class TypedJSONObjectWithFields(JSONObjectWithFields):
    """JSON object with type."""

    typ: str = NotImplemented
    """Type of the object. Subclasses must override."""

    type_field_name: str = "type"
    """Field name used to distinguish different object types.

    Subclasses will probably have to override this.

    """

    TYPES: Dict[str, Type] = NotImplemented
    """Types registered for JSON deserialization"""

    @classmethod
    def register(
        cls, type_cls: Type[GenericTypedJSONObjectWithFields], typ: Optional[str] = None
    ) -> Type[GenericTypedJSONObjectWithFields]:
        """Register class for JSON deserialization."""
        typ = type_cls.typ if typ is None else typ
        cls.TYPES[typ] = type_cls
        return type_cls

    @classmethod
    def get_type_cls(cls, jobj: Mapping[str, Any]) -> Type["TypedJSONObjectWithFields"]:
        """Get the registered class for ``jobj``."""
        if cls in cls.TYPES.values():
            if cls.type_field_name not in jobj:
                raise errors.DeserializationError(
                    "Missing type field ({0})".format(cls.type_field_name)
                )
            # cls is already registered type_cls, force to use it
            # so that, e.g Revocation.from_json(jobj) fails if
            # jobj["type"] != "revocation".
            return cls

        if not isinstance(jobj, dict):
            raise errors.DeserializationError("{0} is not a dictionary object".format(jobj))
        try:
            typ = jobj[cls.type_field_name]
        except KeyError:
            raise errors.DeserializationError("missing type field")

        try:
            return cls.TYPES[typ]
        except KeyError:
            raise errors.UnrecognizedTypeError(typ, jobj)

    def to_partial_json(self) -> Dict[str, Any]:
        """Get JSON serializable object.

        :returns: Serializable JSON object representing ACME typed object.
            :meth:`validate` will almost certainly not work, due to reasons
            explained in :class:`josepy.interfaces.IJSONSerializable`.
        :rtype: dict

        """
        jobj = self.fields_to_partial_json()
        jobj[self.type_field_name] = self.typ
        return jobj

    @classmethod
    def from_json(cls, jobj: Mapping[str, Any]) -> "TypedJSONObjectWithFields":
        """Deserialize ACME object from valid JSON object.

        :raises josepy.errors.UnrecognizedTypeError: if type
            of the ACME object has not been registered.

        """
        # make sure subclasses don't cause infinite recursive from_json calls
        type_cls = cls.get_type_cls(jobj)
        return type_cls(**type_cls.fields_from_json(jobj))
