"""JSON Web Signature."""
import argparse
import base64
import sys
from typing import (
    Any,
    Dict,
    FrozenSet,
    List,
    Mapping,
    Optional,
    Tuple,
    Type,
    cast,
)

from OpenSSL import crypto

import josepy
from josepy import b64, errors, json_util, jwa
from josepy import jwk as jwk_mod
from josepy import util


class MediaType:
    """MediaType field encoder/decoder."""

    PREFIX = "application/"
    """MIME Media Type and Content Type prefix."""

    @classmethod
    def decode(cls, value: str) -> str:
        """Decoder."""
        # 4.1.10
        if "/" not in value:
            if ";" in value:
                raise errors.DeserializationError("Unexpected semi-colon")
            return cls.PREFIX + value
        return value

    @classmethod
    def encode(cls, value: str) -> str:
        """Encoder."""
        # 4.1.10
        if ";" not in value:
            assert value.startswith(cls.PREFIX)
            return value[len(cls.PREFIX) :]
        return value


class Header(json_util.JSONObjectWithFields):
    """JOSE Header.

    .. warning:: This class supports **only** Registered Header
        Parameter Names (as defined in section 4.1 of the
        protocol). If you need Public Header Parameter Names (4.2)
        or Private Header Parameter Names (4.3), you must subclass
        and override :meth:`from_json` and :meth:`to_partial_json`
        appropriately.

    .. warning:: This class does not support any extensions through
        the "crit" (Critical) Header Parameter (4.1.11) and as a
        conforming implementation, :meth:`from_json` treats its
        occurrence as an error. Please subclass if you seek for
        a different behaviour.

    :ivar x5tS256: "x5t#S256"
    :ivar str typ: MIME Media Type, inc. :const:`MediaType.PREFIX`.
    :ivar str cty: Content-Type, inc. :const:`MediaType.PREFIX`.

    """

    alg: Optional[jwa.JWASignature] = json_util.field(
        "alg", decoder=jwa.JWASignature.from_json, omitempty=True
    )
    jku: Optional[bytes] = json_util.field("jku", omitempty=True)
    jwk: Optional[jwk_mod.JWK] = json_util.field(
        "jwk", decoder=jwk_mod.JWK.from_json, omitempty=True
    )
    kid: Optional[str] = json_util.field("kid", omitempty=True)
    x5u: Optional[bytes] = json_util.field("x5u", omitempty=True)
    x5c: Tuple[util.ComparableX509, ...] = json_util.field("x5c", omitempty=True, default=())
    x5t: Optional[bytes] = json_util.field("x5t", decoder=json_util.decode_b64jose, omitempty=True)
    x5tS256: Optional[bytes] = json_util.field(
        "x5t#S256", decoder=json_util.decode_b64jose, omitempty=True
    )
    typ: Optional[MediaType] = json_util.field(
        "typ", encoder=MediaType.encode, decoder=MediaType.decode, omitempty=True
    )
    cty: Optional[MediaType] = json_util.field(
        "cty", encoder=MediaType.encode, decoder=MediaType.decode, omitempty=True
    )
    crit: Tuple[Any, ...] = json_util.field("crit", omitempty=True, default=())
    _fields: Dict[str, json_util.Field]

    def not_omitted(self) -> Dict[str, json_util.Field]:
        """Fields that would not be omitted in the JSON object."""
        return {
            name: getattr(self, name)
            for name, field in self._fields.items()
            if not field.omit(getattr(self, name))
        }

    def __add__(self, other: Any) -> "Header":
        if not isinstance(other, type(self)):
            raise TypeError("Header cannot be added to: {0}".format(type(other)))

        not_omitted_self = self.not_omitted()
        not_omitted_other = other.not_omitted()

        if set(not_omitted_self).intersection(not_omitted_other):
            raise TypeError("Addition of overlapping headers not defined")

        not_omitted_self.update(not_omitted_other)
        return type(self)(**not_omitted_self)

    def find_key(self) -> josepy.JWK:
        """Find key based on header.

        .. todo:: Supports only "jwk" header parameter lookup.

        :returns: (Public) key found in the header.
        :rtype: .JWK

        :raises josepy.errors.Error: if key could not be found

        """
        if self.jwk is None:
            raise errors.Error("No key found")
        return self.jwk

    @crit.decoder  # type: ignore
    def crit(unused_value: Any) -> Any:
        raise errors.DeserializationError('"crit" is not supported, please subclass')

    # x5c does NOT use JOSE Base64 (4.1.6)

    @x5c.encoder  # type: ignore
    def x5c(value):
        return [
            base64.b64encode(crypto.dump_certificate(crypto.FILETYPE_ASN1, cert.wrapped))
            for cert in value
        ]

    @x5c.decoder  # type: ignore
    def x5c(value):
        try:
            return tuple(
                util.ComparableX509(
                    crypto.load_certificate(crypto.FILETYPE_ASN1, base64.b64decode(cert))
                )
                for cert in value
            )
        except crypto.Error as error:
            raise errors.DeserializationError(error)


class Signature(json_util.JSONObjectWithFields):
    """JWS Signature.

    :ivar combined: Combined Header (protected and unprotected,
        :class:`Header`).
    :ivar unicode protected: JWS protected header (Jose Base-64 decoded).
    :ivar header: JWS Unprotected Header (:class:`Header`).
    :ivar str signature: The signature.

    """

    header_cls = Header
    combined: Header

    __slots__ = ("combined",)
    protected: str = json_util.field("protected", omitempty=True, default="")
    header: Header = json_util.field(
        "header", omitempty=True, default=header_cls(), decoder=header_cls.from_json
    )
    signature: bytes = json_util.field(
        "signature", decoder=json_util.decode_b64jose, encoder=json_util.encode_b64jose
    )

    @protected.encoder  # type: ignore
    def protected(value: str) -> str:
        # wrong type guess (Signature, not bytes) | pylint: disable=no-member
        return json_util.encode_b64jose(value.encode("utf-8"))

    @protected.decoder  # type: ignore
    def protected(value: str) -> str:
        return json_util.decode_b64jose(value).decode("utf-8")

    def __init__(self, **kwargs: Any) -> None:
        if "combined" not in kwargs:
            kwargs = self._with_combined(kwargs)
        super().__init__(**kwargs)
        assert self.combined.alg is not None

    @classmethod
    def _with_combined(cls, kwargs: Any) -> Dict[str, Any]:
        assert "combined" not in kwargs
        header = kwargs.get("header", cls._fields["header"].default)
        protected = kwargs.get("protected", cls._fields["protected"].default)

        if protected:
            combined = header + cls.header_cls.json_loads(protected)
        else:
            combined = header

        kwargs["combined"] = combined
        return kwargs

    @classmethod
    def _msg(cls, protected: str, payload: bytes) -> bytes:
        return b64.b64encode(protected.encode("utf-8")) + b"." + b64.b64encode(payload)

    def verify(self, payload: bytes, key: Optional[josepy.JWK] = None) -> bool:
        """Verify.

        :param bytes payload: Payload to verify.
        :param JWK key: Key used for verification.

        """
        actual_key: josepy.JWK = self.combined.find_key() if key is None else key
        if not self.combined.alg:
            raise josepy.Error("Not signature algorithm defined.")
        return self.combined.alg.verify(
            key=actual_key.key, sig=self.signature, msg=self._msg(self.protected, payload)
        )

    @classmethod
    def sign(
        cls,
        payload: bytes,
        key: josepy.JWK,
        alg: josepy.JWASignature,
        include_jwk: bool = True,
        protect: FrozenSet = frozenset(),
        **kwargs: Any,
    ) -> "Signature":
        """Sign.

        :param bytes payload: Payload to sign.
        :param JWK key: Key for signature.
        :param JWASignature alg: Signature algorithm to use to sign.
        :param bool include_jwk: If True, insert the JWK inside the signature headers.
        :param FrozenSet protect: List of headers to protect.

        """
        assert isinstance(key, alg.kty)

        header_params = kwargs
        header_params["alg"] = alg
        if include_jwk:
            header_params["jwk"] = key.public_key()

        assert set(header_params).issubset(cls.header_cls._fields)
        assert protect.issubset(cls.header_cls._fields)

        protected_params = {}
        for header in protect:
            if header in header_params:
                protected_params[header] = header_params.pop(header)
        if protected_params:
            protected = cls.header_cls(**protected_params).json_dumps()
        else:
            protected = ""

        header = cls.header_cls(**header_params)
        signature = alg.sign(key.key, cls._msg(protected, payload))

        return cls(protected=protected, header=header, signature=signature)

    def fields_to_partial_json(self) -> Dict[str, Any]:
        fields = super().fields_to_partial_json()
        if not fields["header"].not_omitted():
            del fields["header"]
        return fields

    @classmethod
    def fields_from_json(cls, jobj: Mapping[str, Any]) -> Dict[str, Any]:
        fields = super().fields_from_json(jobj)
        fields_with_combined = cls._with_combined(fields)
        if "alg" not in fields_with_combined["combined"].not_omitted():
            raise errors.DeserializationError("alg not present")
        return fields_with_combined


class JWS(json_util.JSONObjectWithFields):
    """JSON Web Signature.

    :ivar str payload: JWS Payload.
    :ivar str signature: JWS Signatures.

    """

    __slots__ = ("payload", "signatures")
    payload: bytes
    signatures: List[Signature]

    signature_cls = Signature

    def verify(self, key: Optional[josepy.JWK] = None) -> bool:
        """Verify."""
        return all(sig.verify(self.payload, key) for sig in self.signatures)

    @classmethod
    def sign(cls, payload: bytes, **kwargs: Any) -> "JWS":
        """Sign."""
        return cls(payload=payload, signatures=(cls.signature_cls.sign(payload=payload, **kwargs),))

    @property
    def signature(self) -> Signature:
        """Get a singleton signature.

        :rtype: :class:`JWS.signature_cls`

        """
        assert len(self.signatures) == 1
        return self.signatures[0]

    def to_compact(self) -> bytes:
        """Compact serialization.

        :rtype: bytes

        """
        assert len(self.signatures) == 1

        assert "alg" not in self.signature.header.not_omitted()
        # ... it must be in protected

        return (
            b64.b64encode(self.signature.protected.encode("utf-8"))
            + b"."
            + b64.b64encode(self.payload)
            + b"."
            + b64.b64encode(self.signature.signature)
        )

    @classmethod
    def from_compact(cls, compact: bytes) -> "JWS":
        """Compact deserialization.

        :param bytes compact:

        """
        try:
            protected, payload, signature = compact.split(b".")
        except ValueError:
            raise errors.DeserializationError(
                "Compact JWS serialization should comprise of exactly" " 3 dot-separated components"
            )

        sig = cls.signature_cls(
            protected=b64.b64decode(protected).decode("utf-8"), signature=b64.b64decode(signature)
        )
        return cls(payload=b64.b64decode(payload), signatures=(sig,))

    def to_partial_json(self, flat: bool = True) -> Dict[str, Any]:
        assert self.signatures
        payload = json_util.encode_b64jose(self.payload)

        if flat and len(self.signatures) == 1:
            ret = self.signatures[0].to_partial_json()
            ret["payload"] = payload
            return ret
        else:
            return {
                "payload": payload,
                "signatures": self.signatures,
            }

    @classmethod
    def from_json(cls, jobj: Mapping[str, Any]) -> "JWS":
        if "signature" in jobj and "signatures" in jobj:
            raise errors.DeserializationError("Flat mixed with non-flat")
        elif "signature" in jobj:  # flat
            filtered = {key: value for key, value in jobj.items() if key != "payload"}
            return cls(
                payload=json_util.decode_b64jose(jobj["payload"]),
                signatures=(cls.signature_cls.from_json(filtered),),
            )
        else:
            return cls(
                payload=json_util.decode_b64jose(jobj["payload"]),
                signatures=tuple(cls.signature_cls.from_json(sig) for sig in jobj["signatures"]),
            )


class CLI:
    """JWS CLI."""

    @classmethod
    def sign(cls, args: argparse.Namespace) -> None:
        """Sign."""
        key = args.alg.kty.load(args.key.read())
        args.key.close()
        if args.protect is None:
            args.protect = []
        if args.compact:
            args.protect.append("alg")

        sig = JWS.sign(
            payload=sys.stdin.read().encode(), key=key, alg=args.alg, protect=set(args.protect)
        )

        if args.compact:
            print(sig.to_compact().decode("utf-8"))
        else:  # JSON
            print(sig.json_dumps_pretty())

    @classmethod
    def verify(cls, args: argparse.Namespace) -> bool:
        """Verify."""
        if args.compact:
            sig = JWS.from_compact(sys.stdin.read().encode())
        else:  # JSON
            try:
                sig = cast(JWS, JWS.json_loads(sys.stdin.read()))
            except errors.Error as error:
                print(error)
                return False

        if args.key is not None:
            assert args.kty is not None
            key = args.kty.load(args.key.read()).public_key()
            args.key.close()
        else:
            key = None

        sys.stdout.write(sig.payload.decode())
        return not sig.verify(key=key)

    @classmethod
    def _alg_type(cls, arg: Any) -> jwa.JWASignature:
        return jwa.JWASignature.from_json(arg)

    @classmethod
    def _header_type(cls, arg: Any) -> Any:
        assert arg in Signature.header_cls._fields
        return arg

    @classmethod
    def _kty_type(cls, arg: Any) -> Type[jwk_mod.JWK]:
        assert arg in jwk_mod.JWK.TYPES
        return jwk_mod.JWK.TYPES[arg]

    @classmethod
    def run(cls, args: Optional[List[str]] = None) -> Optional[bool]:
        """Parse arguments and sign/verify."""
        if args is None:
            args = sys.argv[1:]
        parser = argparse.ArgumentParser()
        parser.add_argument("--compact", action="store_true")

        subparsers = parser.add_subparsers()
        parser_sign = subparsers.add_parser("sign")
        parser_sign.set_defaults(func=cls.sign)
        parser_sign.add_argument("-k", "--key", type=argparse.FileType("rb"), required=True)
        parser_sign.add_argument("-a", "--alg", type=cls._alg_type, default=jwa.RS256)
        parser_sign.add_argument("-p", "--protect", action="append", type=cls._header_type)

        parser_verify = subparsers.add_parser("verify")
        parser_verify.set_defaults(func=cls.verify)
        parser_verify.add_argument("-k", "--key", type=argparse.FileType("rb"), required=False)
        parser_verify.add_argument("--kty", type=cls._kty_type, required=False)

        parsed = parser.parse_args(args)
        return parsed.func(parsed)


if __name__ == "__main__":
    exit(CLI.run())  # pragma: no cover
