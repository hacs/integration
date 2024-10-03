from typing import Any, Callable, Dict, Type, TypeVar, Union, final

import orjson

from mashumaro.dialect import Dialect
from mashumaro.mixins.dict import DataClassDictMixin

T = TypeVar("T", bound="DataClassORJSONMixin")

EncodedData = Union[str, bytes, bytearray]
Encoder = Callable[[Any], EncodedData]
Decoder = Callable[[EncodedData], Dict[Any, Any]]

class OrjsonDialect(Dialect):
    serialization_strategy: Any

class DataClassORJSONMixin(DataClassDictMixin):
    __slots__ = ()
    @final
    def to_jsonb(
        self: T,
        encoder: Encoder = orjson.dumps,
        *,
        orjson_options: int = ...,
        **to_dict_kwargs: Any,
    ) -> bytes: ...
    def to_json(
        self: T,
        encoder: Encoder = orjson.dumps,
        *,
        orjson_options: int = ...,
        **to_dict_kwargs: Any,
    ) -> str: ...
    @classmethod
    @final
    def from_json(
        cls: Type[T],
        data: EncodedData,
        decoder: Decoder = orjson.loads,
        **from_dict_kwargs: Any,
    ) -> T: ...
