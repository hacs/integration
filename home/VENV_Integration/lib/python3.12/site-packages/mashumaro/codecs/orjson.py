from typing import (
    Any,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    final,
    overload,
)

import orjson

from mashumaro.codecs._builder import CodecCodeBuilder
from mashumaro.core.meta.helpers import get_args
from mashumaro.dialect import Dialect
from mashumaro.mixins.orjson import OrjsonDialect

T = TypeVar("T")
EncodedData = Union[str, bytes, bytearray]


class ORJSONDecoder(Generic[T]):
    @overload
    def __init__(
        self,
        shape_type: Type[T],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
    ): ...

    @overload
    def __init__(
        self,
        shape_type: Any,
        *,
        default_dialect: Optional[Type[Dialect]] = None,
    ): ...

    def __init__(
        self,
        shape_type: Union[Type[T], Any],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
    ):
        if default_dialect is not None:
            default_dialect = OrjsonDialect.merge(default_dialect)
        else:
            default_dialect = OrjsonDialect
        code_builder = CodecCodeBuilder.new(
            type_args=get_args(shape_type), default_dialect=default_dialect
        )
        code_builder.add_decode_method(shape_type, self, orjson.loads)

    @final
    def decode(self, data: EncodedData) -> T: ...


class ORJSONEncoder(Generic[T]):
    @overload
    def __init__(
        self,
        shape_type: Type[T],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
    ): ...

    @overload
    def __init__(
        self,
        shape_type: Any,
        *,
        default_dialect: Optional[Type[Dialect]] = None,
    ): ...

    def __init__(
        self,
        shape_type: Union[Type[T], Any],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
    ):
        if default_dialect is not None:
            default_dialect = OrjsonDialect.merge(default_dialect)
        else:
            default_dialect = OrjsonDialect
        code_builder = CodecCodeBuilder.new(
            type_args=get_args(shape_type), default_dialect=default_dialect
        )
        code_builder.add_encode_method(shape_type, self, orjson.dumps)

    @final
    def encode(self, obj: T) -> bytes: ...


def json_decode(data: EncodedData, shape_type: Type[T]) -> T:
    return ORJSONDecoder(shape_type).decode(data)


def json_encode(obj: T, shape_type: Union[Type[T], Any]) -> bytes:
    return ORJSONEncoder(shape_type).encode(obj)


decode = json_decode
encode = json_encode


__all__ = [
    "ORJSONDecoder",
    "ORJSONEncoder",
    "json_decode",
    "json_encode",
    "decode",
    "encode",
]
