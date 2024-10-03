import json
from typing import Any, Callable, Dict, Type, TypeVar, Union

from mashumaro.mixins.dict import DataClassDictMixin

T = TypeVar("T", bound="DataClassJSONMixin")


EncodedData = Union[str, bytes, bytearray]
Encoder = Callable[[Any], EncodedData]
Decoder = Callable[[EncodedData], Dict[Any, Any]]


class DataClassJSONMixin(DataClassDictMixin):
    __slots__ = ()

    def to_json(
        self: T,
        encoder: Encoder = json.dumps,
        **to_dict_kwargs: Any,
    ) -> EncodedData:
        return encoder(self.to_dict(**to_dict_kwargs))

    @classmethod
    def from_json(
        cls: Type[T],
        data: EncodedData,
        decoder: Decoder = json.loads,
        **from_dict_kwargs: Any,
    ) -> T:
        return cls.from_dict(decoder(data), **from_dict_kwargs)
