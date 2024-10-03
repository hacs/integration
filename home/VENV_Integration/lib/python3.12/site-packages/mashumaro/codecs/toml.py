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

import tomli_w

from mashumaro.codecs._builder import CodecCodeBuilder
from mashumaro.core.meta.helpers import get_args
from mashumaro.dialect import Dialect
from mashumaro.mixins.toml import TOMLDialect

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore

T = TypeVar("T")
EncodedData = str


class TOMLDecoder(Generic[T]):
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
            default_dialect = TOMLDialect.merge(default_dialect)
        else:
            default_dialect = TOMLDialect
        code_builder = CodecCodeBuilder.new(
            type_args=get_args(shape_type), default_dialect=default_dialect
        )
        code_builder.add_decode_method(shape_type, self, tomllib.loads)

    @final
    def decode(self, data: EncodedData) -> T: ...


class TOMLEncoder(Generic[T]):
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
            default_dialect = TOMLDialect.merge(default_dialect)
        else:
            default_dialect = TOMLDialect
        code_builder = CodecCodeBuilder.new(
            type_args=get_args(shape_type), default_dialect=default_dialect
        )
        code_builder.add_encode_method(shape_type, self, tomli_w.dumps)

    @final
    def encode(self, obj: T) -> bytes: ...


def toml_decode(data: EncodedData, shape_type: Type[T]) -> T:
    return TOMLDecoder(shape_type).decode(data)


def toml_encode(obj: T, shape_type: Union[Type[T], Any]) -> bytes:
    return TOMLEncoder(shape_type).encode(obj)


decode = toml_decode
encode = toml_encode


__all__ = [
    "TOMLDecoder",
    "TOMLEncoder",
    "toml_decode",
    "toml_encode",
    "decode",
    "encode",
]
