from dataclasses import dataclass
from typing import Dict, Set

from mashumaro.jsonschema.models import JSONSchema, Number


class Annotation:
    pass


class Constraint(Annotation):
    pass


class NumberConstraint(Constraint):
    pass


@dataclass(unsafe_hash=True)
class Minimum(NumberConstraint):
    value: Number


@dataclass(unsafe_hash=True)
class Maximum(NumberConstraint):
    value: Number


@dataclass(unsafe_hash=True)
class ExclusiveMinimum(NumberConstraint):
    value: Number


@dataclass(unsafe_hash=True)
class ExclusiveMaximum(NumberConstraint):
    value: Number


@dataclass(unsafe_hash=True)
class MultipleOf(NumberConstraint):
    value: Number


class StringConstraint(Constraint):
    pass


@dataclass(unsafe_hash=True)
class MinLength(StringConstraint):
    value: int


@dataclass(unsafe_hash=True)
class MaxLength(StringConstraint):
    value: int


@dataclass(unsafe_hash=True)
class Pattern(StringConstraint):
    value: str


class ArrayConstraint(Constraint):
    pass


@dataclass(unsafe_hash=True)
class MinItems(ArrayConstraint):
    value: int


@dataclass(unsafe_hash=True)
class MaxItems(ArrayConstraint):
    value: int


@dataclass(unsafe_hash=True)
class UniqueItems(ArrayConstraint):
    value: bool


@dataclass(unsafe_hash=True)
class Contains(ArrayConstraint):
    value: JSONSchema


@dataclass(unsafe_hash=True)
class MinContains(ArrayConstraint):
    value: int


@dataclass(unsafe_hash=True)
class MaxContains(ArrayConstraint):
    value: int


class ObjectConstraint(Constraint):
    pass


@dataclass(unsafe_hash=True)
class MaxProperties(ObjectConstraint):
    value: int


@dataclass(unsafe_hash=True)
class MinProperties(ObjectConstraint):
    value: int


@dataclass
class DependentRequired(ObjectConstraint):
    value: Dict[str, Set[str]]


__all__ = [
    "Annotation",
    "MultipleOf",
    "Maximum",
    "ExclusiveMaximum",
    "Minimum",
    "ExclusiveMinimum",
    "MaxLength",
    "MinLength",
    "Pattern",
    "MaxItems",
    "MinItems",
    "UniqueItems",
    "Contains",
    "MaxContains",
    "MinContains",
    "MaxProperties",
    "MinProperties",
    "DependentRequired",
]
