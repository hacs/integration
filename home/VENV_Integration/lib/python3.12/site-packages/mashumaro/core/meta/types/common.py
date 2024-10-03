import collections.abc
import re
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from functools import cached_property
from types import new_class
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
)

from typing_extensions import ParamSpec, TypeAlias

from mashumaro.core.const import PEP_585_COMPATIBLE
from mashumaro.core.meta.code.lines import CodeLines
from mashumaro.core.meta.helpers import (
    get_args,
    get_type_origin,
    is_annotated,
    is_generic,
    is_hashable_type,
    is_self,
    type_name,
)
from mashumaro.exceptions import UnserializableField

if TYPE_CHECKING:  # pragma: no cover
    from mashumaro.core.meta.code.builder import CodeBuilder
else:
    CodeBuilder = Any


NoneType = type(None)
Expression: TypeAlias = str

P = ParamSpec("P")
T = TypeVar("T")

_PY_VALID_ID_RE = re.compile(r"\W|^(?=\d)")


class AttrsHolder:
    def __new__(
        cls, name: Optional[str] = None, *args: Any, **kwargs: Any
    ) -> Any:
        ah = new_class("AttrsHolder")
        ah_id = id(ah)
        if not name:
            name = f"attrs_{ah_id}"
        ah.__name__ = ah.__qualname__ = name
        return ah


class ExpressionWrapper:
    def __init__(self, expression: str):
        self.expression = expression


PROPER_COLLECTION_TYPES: Dict[Type, str] = {
    tuple: "typing.Tuple[T]",
    list: "typing.List[T]",
    set: "typing.Set[T]",
    frozenset: "typing.FrozenSet[T]",
    dict: "typing.Dict[KT,VT] or Mapping[KT,VT]",
    collections.deque: "typing.Deque[T]",
    collections.ChainMap: "typing.ChainMap[KT,VT]",
    collections.OrderedDict: "typing.OrderedDict[KT,VT]",
    collections.defaultdict: "typing.DefaultDict[KT, VT]",
    collections.Counter: "typing.Counter[KT]",
}


@dataclass
class FieldContext:
    name: str
    metadata: Mapping

    def copy(self, **changes: Any) -> "FieldContext":
        return replace(self, **changes)


@dataclass
class ValueSpec:
    type: Type
    origin_type: Type = field(init=False)
    expression: Expression
    builder: CodeBuilder
    field_ctx: FieldContext
    could_be_none: bool = True
    annotated_type: Optional[Type] = None
    owner: Optional[Type] = None
    no_copy_collections: Sequence = tuple()

    def __setattr__(self, key: str, value: Any) -> None:
        if key == "type":
            self.origin_type = get_type_origin(value)
        super().__setattr__(key, value)

    def copy(self, **changes: Any) -> "ValueSpec":
        return replace(self, **changes)

    @cached_property
    def annotations(self) -> Sequence[str]:
        return getattr(self.annotated_type, "__metadata__", [])

    @cached_property
    def attrs(self) -> Any:
        if self.builder.is_nailed:
            return self.builder.attrs
        if is_self(self.type):
            typ = self.builder.cls
        else:
            typ = self.origin_type
        attrs = self.attrs_registry.get(typ)
        if attrs is None:
            attrs = AttrsHolder()
            self.attrs_registry[typ] = attrs
        return attrs

    @cached_property
    def cls_attrs_name(self) -> str:
        if self.builder.is_nailed:
            return "cls"
        else:
            self.builder.ensure_object_imported(self.attrs)
            return self.attrs.__name__

    @cached_property
    def self_attrs_name(self) -> str:
        if self.builder.is_nailed:
            return "self"
        else:
            self.builder.ensure_object_imported(self.attrs)
            return self.attrs.__name__

    @cached_property
    def attrs_registry(self) -> Dict[Any, Any]:
        return self.builder.attrs_registry

    @cached_property
    def attrs_registry_name(self) -> str:
        name = f"attrs_registry_{id(self.attrs_registry)}"
        self.builder.ensure_object_imported(self.attrs_registry, name)
        return name


class AbstractMethodBuilder(ABC):
    @abstractmethod
    def get_method_prefix(self) -> str:  # pragma: no cover
        raise NotImplementedError

    def _generate_method_name(
        self, spec: ValueSpec
    ) -> str:  # pragma: no cover
        prefix = self.get_method_prefix()
        if prefix:
            prefix = f"{prefix}_"
        if spec.field_ctx.name:
            suffix = f"_{spec.field_ctx.name}"
        else:
            suffix = ""
        return f"__{prefix}{spec.builder.cls.__name__}{suffix}__{random_hex()}"

    @abstractmethod
    def _add_definition(self, spec: ValueSpec, lines: CodeLines) -> str:
        raise NotImplementedError

    @abstractmethod
    def _generate_method_args(self, spec: ValueSpec) -> str:
        raise NotImplementedError

    @abstractmethod
    def _add_body(
        self, spec: ValueSpec, lines: CodeLines
    ) -> None:  # pragma: no cover
        raise NotImplementedError

    def _add_setattr(
        self, spec: ValueSpec, method_name: str, lines: CodeLines
    ) -> None:
        lines.append(
            f"setattr({spec.cls_attrs_name}, '{method_name}', {method_name})"
        )

    def _compile(self, spec: ValueSpec, lines: CodeLines) -> None:
        if spec.builder.get_config().debug:
            print(f"{type_name(spec.builder.cls)}:")
            print(lines.as_text())
        exec(lines.as_text(), spec.builder.globals, spec.builder.__dict__)

    @abstractmethod
    def _get_call_expr(self, spec: ValueSpec, method_name: str) -> str:
        raise NotImplementedError

    def _before_build(self, spec: ValueSpec) -> None:
        pass

    def build(self, spec: ValueSpec) -> str:
        self._before_build(spec)
        lines = CodeLines()
        method_name = self._add_definition(spec, lines)
        with lines.indent():
            self._add_body(spec, lines)
        self._add_setattr(spec, method_name, lines)
        self._compile(spec, lines)
        return self._get_call_expr(spec, method_name)


ValueSpecExprCreator: TypeAlias = Callable[[ValueSpec], Optional[Expression]]


@dataclass
class Registry:
    _registry: List[ValueSpecExprCreator] = field(default_factory=list)

    def register(self, function: ValueSpecExprCreator) -> ValueSpecExprCreator:
        self._registry.append(function)
        return function

    def get(self, spec: ValueSpec) -> Expression:
        if is_annotated(spec.type):
            spec.annotated_type = spec.builder.get_real_type(
                spec.field_ctx.name, spec.type
            )
            spec.type = get_type_origin(spec.type)
        spec.type = spec.builder.get_real_type(spec.field_ctx.name, spec.type)
        spec.builder.add_type_modules(spec.type)
        for packer in self._registry:
            expr = packer(spec)
            if expr is not None:
                return expr
        raise UnserializableField(
            spec.field_ctx.name, spec.type, spec.builder.cls
        )


def ensure_generic_collection(spec: ValueSpec) -> bool:
    if not PEP_585_COMPATIBLE and not get_args(spec.type):
        proper_type = PROPER_COLLECTION_TYPES.get(spec.type)
        if proper_type:
            raise UnserializableField(
                field_name=spec.field_ctx.name,
                field_type=spec.type,
                holder_class=spec.builder.cls,
                msg=f"Use {proper_type} instead",
            )
    if not is_generic(spec.type):
        return False
    return True


def ensure_mapping_key_type_hashable(
    spec: ValueSpec, type_args: Sequence[Type]
) -> bool:
    if type_args:
        first_type_arg = type_args[0]
        if not is_hashable_type(first_type_arg):
            raise UnserializableField(
                field_name=spec.field_ctx.name,
                field_type=spec.type,
                holder_class=spec.builder.cls,
                msg=(
                    f"{type_name(first_type_arg, short=True)} "
                    "is unhashable and can not be used as a key"
                ),
            )
    return True


def ensure_generic_collection_subclass(
    spec: ValueSpec, *checked_types: Type
) -> bool:
    return issubclass(
        spec.origin_type, checked_types
    ) and ensure_generic_collection(spec)


def ensure_generic_mapping(
    spec: ValueSpec, args: Sequence[Type], checked_type: Type
) -> bool:
    return ensure_generic_collection_subclass(
        spec, checked_type
    ) and ensure_mapping_key_type_hashable(spec, args)


def expr_or_maybe_none(spec: ValueSpec, new_expr: Expression) -> Expression:
    if spec.could_be_none:
        return f"{new_expr} if {spec.expression} is not None else None"
    else:
        return new_expr


def random_hex() -> str:
    return str(uuid.uuid4().hex)


def clean_id(value: str) -> str:
    if not value:
        return "_"

    return _PY_VALID_ID_RE.sub("_", value)
