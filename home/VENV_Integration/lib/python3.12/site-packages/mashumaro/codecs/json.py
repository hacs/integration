import json
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
    final,
    overload,
)

from mashumaro.codecs._builder import CodecCodeBuilder
from mashumaro.core.meta.helpers import get_args
from mashumaro.dialect import Dialect

T = TypeVar("T")
EncodedData = Union[str, bytes, bytearray]


class JSONDecoder(Generic[T]):
    @overload
    def __init__(
        self,
        shape_type: Type[T],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        pre_decoder_func: Callable[[EncodedData], Any] = json.loads,
    ): ...

    @overload
    def __init__(
        self,
        shape_type: Any,
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        pre_decoder_func: Callable[[EncodedData], Any] = json.loads,
    ): ...

    def __init__(
        self,
        shape_type: Union[Type[T], Any],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        pre_decoder_func: Callable[[EncodedData], Any] = json.loads,
    ):
        code_builder = CodecCodeBuilder.new(
            type_args=get_args(shape_type), default_dialect=default_dialect
        )
        code_builder.add_decode_method(shape_type, self, pre_decoder_func)

    @final
    def decode(self, data: EncodedData) -> T: ...


class JSONEncoder(Generic[T]):
    @overload
    def __init__(
        self,
        shape_type: Type[T],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        post_encoder_func: Callable[[Any], str] = json.dumps,
    ): ...

    @overload
    def __init__(
        self,
        shape_type: Any,
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        post_encoder_func: Callable[[Any], str] = json.dumps,
    ): ...

    def __init__(
        self,
        shape_type: Union[Type[T], Any],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        post_encoder_func: Callable[[Any], str] = json.dumps,
    ):
        code_builder = CodecCodeBuilder.new(
            type_args=get_args(shape_type), default_dialect=default_dialect
        )
        code_builder.add_encode_method(shape_type, self, post_encoder_func)

    @final
    def encode(self, obj: T) -> str: ...


def json_decode(
    data: EncodedData,
    shape_type: Union[Type[T], Any],
    pre_decoder_func: Callable[[EncodedData], Any] = json.loads,
) -> T:
    return JSONDecoder(shape_type, pre_decoder_func=pre_decoder_func).decode(
        data
    )


def json_encode(
    obj: T,
    shape_type: Union[Type[T], Any],
    post_encoder_func: Callable[[Any], str] = json.dumps,
) -> str:
    return JSONEncoder(shape_type, post_encoder_func=post_encoder_func).encode(
        obj
    )


decode = json_decode
encode = json_encode


__all__ = [
    "JSONDecoder",
    "JSONEncoder",
    "json_decode",
    "json_encode",
    "decode",
    "encode",
]
