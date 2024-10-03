from types import new_class
from typing import Any, Callable, Dict, Sequence, Type, Union, cast

from typing_extensions import Literal

from mashumaro.core.const import Sentinel
from mashumaro.types import SerializationStrategy

__all__ = ["Dialect"]


SerializationStrategyValueType = Union[
    SerializationStrategy, Dict[str, Union[str, Callable]]
]


class Dialect:
    serialization_strategy: Dict[Any, SerializationStrategyValueType] = {}
    serialize_by_alias: Union[bool, Literal[Sentinel.MISSING]] = (
        Sentinel.MISSING
    )
    namedtuple_as_dict: Union[bool, Literal[Sentinel.MISSING]] = (
        Sentinel.MISSING
    )
    omit_none: Union[bool, Literal[Sentinel.MISSING]] = Sentinel.MISSING
    omit_default: Union[bool, Literal[Sentinel.MISSING]] = Sentinel.MISSING
    no_copy_collections: Union[Sequence[Any], Literal[Sentinel.MISSING]] = (
        Sentinel.MISSING
    )

    @classmethod
    def merge(cls, other: Type["Dialect"]) -> Type["Dialect"]:
        serialization_strategy: Dict[Any, SerializationStrategyValueType] = {}
        for key, value in cls.serialization_strategy.items():
            if isinstance(value, SerializationStrategy):
                serialization_strategy[key] = value
            else:
                serialization_strategy[key] = value.copy()
        for key, value in other.serialization_strategy.items():
            if isinstance(value, SerializationStrategy):
                serialization_strategy[key] = value
            elif isinstance(
                serialization_strategy.get(key), SerializationStrategy
            ):
                serialization_strategy[key] = value
            else:
                (
                    serialization_strategy.setdefault(
                        key, {}
                    ).update(  # type: ignore
                        value
                    )
                )
        new_dialect = cast(Type[Dialect], new_class("Dialect", (Dialect,)))
        new_dialect.serialization_strategy = serialization_strategy
        for key in ("omit_none", "omit_default", "no_copy_collections"):
            if (others_value := getattr(other, key)) is not Sentinel.MISSING:
                setattr(new_dialect, key, others_value)
            else:
                setattr(new_dialect, key, getattr(cls, key))
        return new_dialect
