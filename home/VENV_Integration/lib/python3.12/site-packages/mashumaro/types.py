import decimal
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Type, Union

from typing_extensions import Literal

from mashumaro.core.const import Sentinel

__all__ = [
    "SerializableType",
    "GenericSerializableType",
    "SerializationStrategy",
    "RoundedDecimal",
    "Discriminator",
    "Alias",
]


class SerializableType:
    __slots__ = ()

    __use_annotations__ = False

    def __init_subclass__(
        cls,
        use_annotations: Union[
            bool, Literal[Sentinel.MISSING]
        ] = Sentinel.MISSING,
        **kwargs: Any,
    ):
        if use_annotations is not Sentinel.MISSING:
            cls.__use_annotations__ = use_annotations

    def _serialize(self) -> Any:
        raise NotImplementedError

    @classmethod
    def _deserialize(cls, value: Any) -> Any:
        raise NotImplementedError


class GenericSerializableType:
    __slots__ = ()

    def _serialize(self, types: List[Type]) -> Any:
        raise NotImplementedError

    @classmethod
    def _deserialize(cls, value: Any, types: List[Type]) -> Any:
        raise NotImplementedError


class SerializationStrategy:
    __use_annotations__ = False

    def __init_subclass__(
        cls,
        use_annotations: Union[
            bool, Literal[Sentinel.MISSING]
        ] = Sentinel.MISSING,
        **kwargs: Any,
    ):
        if use_annotations is not Sentinel.MISSING:
            cls.__use_annotations__ = use_annotations

    def serialize(self, value: Any) -> Any:
        raise NotImplementedError

    def deserialize(self, value: Any) -> Any:
        raise NotImplementedError


class RoundedDecimal(SerializationStrategy):
    def __init__(
        self, places: Optional[int] = None, rounding: Optional[str] = None
    ):
        if places is not None:
            self.exp = decimal.Decimal((0, (1,), -places))
        else:
            self.exp = None  # type: ignore
        self.rounding = rounding

    def serialize(self, value: decimal.Decimal) -> str:
        if self.exp:
            if self.rounding:
                return str(value.quantize(self.exp, rounding=self.rounding))
            else:
                return str(value.quantize(self.exp))
        else:
            return str(value)

    def deserialize(self, value: str) -> decimal.Decimal:
        return decimal.Decimal(str(value))


@dataclass(unsafe_hash=True)
class Discriminator:
    field: Optional[str] = None
    include_supertypes: bool = False
    include_subtypes: bool = False
    variant_tagger_fn: Optional[Callable[[Any], Any]] = None

    def __post_init__(self) -> None:
        if not self.include_supertypes and not self.include_subtypes:
            raise ValueError(
                "Either 'include_supertypes' or 'include_subtypes' "
                "must be enabled"
            )


class Alias:
    def __init__(self, name: str, /):
        self.name = name

    def __repr__(self) -> str:
        return f"Alias(name='{self.name}')"

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Alias):
            return False
        return self.name == other.name

    def __hash__(self) -> int:
        return hash(self.name)
