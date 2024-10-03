from typing import Any, Callable, Dict, Type, TypeVar, Union

import yaml

from mashumaro.mixins.dict import DataClassDictMixin

T = TypeVar("T", bound="DataClassYAMLMixin")


EncodedData = Union[str, bytes]
Encoder = Callable[[Any], EncodedData]
Decoder = Callable[[EncodedData], Dict[Any, Any]]


DefaultLoader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
DefaultDumper = getattr(yaml, "CDumper", yaml.Dumper)


def default_encoder(data: Any) -> EncodedData:
    return yaml.dump(data, Dumper=DefaultDumper)


def default_decoder(data: EncodedData) -> Dict[Any, Any]:
    return yaml.load(data, DefaultLoader)


class DataClassYAMLMixin(DataClassDictMixin):
    __slots__ = ()

    def to_yaml(
        self: T,
        encoder: Encoder = default_encoder,
        **to_dict_kwargs: Any,
    ) -> EncodedData:
        return encoder(self.to_dict(**to_dict_kwargs))

    @classmethod
    def from_yaml(
        cls: Type[T],
        data: EncodedData,
        decoder: Decoder = default_decoder,
        **from_dict_kwargs: Any,
    ) -> T:
        return cls.from_dict(decoder(data), **from_dict_kwargs)
