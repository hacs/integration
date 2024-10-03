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

import msgpack

from mashumaro.codecs._builder import CodecCodeBuilder
from mashumaro.core.meta.helpers import get_args
from mashumaro.dialect import Dialect
from mashumaro.mixins.msgpack import MessagePackDialect

T = TypeVar("T")

EncodedData = bytes
PostEncoderFunc = Callable[[Any], EncodedData]
PreDecoderFunc = Callable[[EncodedData], Any]


def _default_decoder(data: EncodedData) -> Any:
    return msgpack.unpackb(data, raw=False)


def _default_encoder(data: Any) -> EncodedData:
    return msgpack.packb(data, use_bin_type=True)


class MessagePackDecoder(Generic[T]):
    @overload
    def __init__(
        self,
        shape_type: Type[T],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        pre_decoder_func: Optional[PreDecoderFunc] = _default_decoder,
    ): ...

    @overload
    def __init__(
        self,
        shape_type: Any,
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        pre_decoder_func: Optional[PreDecoderFunc] = _default_decoder,
    ): ...

    def __init__(
        self,
        shape_type: Union[Type[T], Any],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        pre_decoder_func: Optional[PreDecoderFunc] = _default_decoder,
    ):
        if default_dialect is not None:
            default_dialect = MessagePackDialect.merge(default_dialect)
        else:
            default_dialect = MessagePackDialect
        code_builder = CodecCodeBuilder.new(
            type_args=get_args(shape_type), default_dialect=default_dialect
        )
        code_builder.add_decode_method(shape_type, self, pre_decoder_func)

    @final
    def decode(self, data: EncodedData) -> T: ...


class MessagePackEncoder(Generic[T]):
    @overload
    def __init__(
        self,
        shape_type: Type[T],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        post_encoder_func: Optional[PostEncoderFunc] = _default_encoder,
    ): ...

    @overload
    def __init__(
        self,
        shape_type: Any,
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        post_encoder_func: Optional[PostEncoderFunc] = _default_encoder,
    ): ...

    def __init__(
        self,
        shape_type: Union[Type[T], Any],
        *,
        default_dialect: Optional[Type[Dialect]] = None,
        post_encoder_func: Optional[PostEncoderFunc] = _default_encoder,
    ):
        if default_dialect is not None:
            default_dialect = MessagePackDialect.merge(default_dialect)
        else:
            default_dialect = MessagePackDialect
        code_builder = CodecCodeBuilder.new(
            type_args=get_args(shape_type), default_dialect=default_dialect
        )
        code_builder.add_encode_method(shape_type, self, post_encoder_func)

    @final
    def encode(self, obj: T) -> EncodedData: ...


def msgpack_decode(data: EncodedData, shape_type: Union[Type[T], Any]) -> T:
    return MessagePackDecoder(shape_type).decode(data)


def msgpack_encode(obj: T, shape_type: Union[Type[T], Any]) -> EncodedData:
    return MessagePackEncoder(shape_type).encode(obj)


decode = msgpack_decode
encode = msgpack_encode


__all__ = [
    "MessagePackDecoder",
    "MessagePackEncoder",
    "msgpack_decode",
    "msgpack_encode",
    "decode",
    "encode",
]
