from typing import Any, Callable, Dict, Type, TypeVar, final

import msgpack

from mashumaro.dialect import Dialect
from mashumaro.helper import pass_through
from mashumaro.mixins.dict import DataClassDictMixin

T = TypeVar("T", bound="DataClassMessagePackMixin")


EncodedData = bytes
Encoder = Callable[[Any], EncodedData]
Decoder = Callable[[EncodedData], Dict[Any, Any]]


class MessagePackDialect(Dialect):
    no_copy_collections = (list, dict)
    serialization_strategy = {
        bytes: pass_through,
        bytearray: {
            "deserialize": bytearray,
            "serialize": pass_through,
        },
    }


def default_encoder(data: Any) -> EncodedData:
    return msgpack.packb(data, use_bin_type=True)


def default_decoder(data: EncodedData) -> Dict[Any, Any]:
    return msgpack.unpackb(data, raw=False)


class DataClassMessagePackMixin(DataClassDictMixin):
    __slots__ = ()

    __mashumaro_builder_params = {
        "packer": {
            "format_name": "msgpack",
            "dialect": MessagePackDialect,
            "encoder": default_encoder,
        },
        "unpacker": {
            "format_name": "msgpack",
            "dialect": MessagePackDialect,
            "decoder": default_decoder,
        },
    }

    @final
    def to_msgpack(
        self: T,
        encoder: Encoder = default_encoder,
        **to_dict_kwargs: Any,
    ) -> EncodedData: ...

    @classmethod
    @final
    def from_msgpack(
        cls: Type[T],
        data: EncodedData,
        decoder: Decoder = default_decoder,
        **from_dict_kwargs: Any,
    ) -> T: ...
