import datetime
import enum
import ipaddress
import os
import typing
import uuid
from base64 import encodebytes
from contextlib import suppress
from dataclasses import is_dataclass
from decimal import Decimal
from fractions import Fraction
from typing import (
    Any,
    Callable,
    Dict,
    ForwardRef,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

import typing_extensions

from mashumaro.core.const import PY_39_MIN, PY_311_MIN
from mashumaro.core.meta.code.lines import CodeLines
from mashumaro.core.meta.helpers import (
    get_args,
    get_class_that_defines_method,
    get_function_return_annotation,
    get_literal_values,
    get_type_origin,
    get_type_var_default,
    is_final,
    is_generic,
    is_literal,
    is_named_tuple,
    is_new_type,
    is_not_required,
    is_optional,
    is_required,
    is_self,
    is_special_typing_primitive,
    is_type_alias_type,
    is_type_var,
    is_type_var_any,
    is_type_var_tuple,
    is_typed_dict,
    is_union,
    is_unpack,
    not_none_type_arg,
    resolve_type_params,
    substitute_type_params,
    type_name,
    type_var_has_default,
)
from mashumaro.core.meta.types.common import (
    Expression,
    ExpressionWrapper,
    NoneType,
    Registry,
    ValueSpec,
    clean_id,
    ensure_generic_collection,
    ensure_generic_collection_subclass,
    ensure_generic_mapping,
    expr_or_maybe_none,
    random_hex,
)
from mashumaro.exceptions import (
    UnserializableDataError,
    UnserializableField,
    UnsupportedSerializationEngine,
)
from mashumaro.helper import pass_through
from mashumaro.types import (
    GenericSerializableType,
    SerializableType,
    SerializationStrategy,
)

if PY_39_MIN:
    import zoneinfo


__all__ = ["PackerRegistry"]


PackerRegistry = Registry()
register = PackerRegistry.register


def _pack_with_annotated_serialization_strategy(
    spec: ValueSpec,
    strategy: SerializationStrategy,
) -> Expression:
    strategy_type = type(strategy)
    try:
        value_type: Union[Type, Any] = get_function_return_annotation(
            strategy.serialize
        )
    except (KeyError, ValueError):
        value_type = Any
    if isinstance(value_type, ForwardRef):
        value_type = spec.builder.evaluate_forward_ref(
            value_type, spec.origin_type
        )
    value_type = substitute_type_params(
        value_type,  # type: ignore
        resolve_type_params(strategy_type, get_args(spec.type))[strategy_type],
    )
    overridden_fn = f"__{spec.field_ctx.name}_serialize_{random_hex()}"
    setattr(spec.attrs, overridden_fn, strategy.serialize)
    new_spec = spec.copy(
        type=value_type,
        expression=(
            f"{spec.self_attrs_name}.{overridden_fn}({spec.expression})"
        ),
    )
    field_metadata = new_spec.field_ctx.metadata
    if field_metadata.get("serialization_strategy") is strategy:
        new_spec.field_ctx.metadata = {
            k: v
            for k, v in field_metadata.items()
            if k != "serialization_strategy"
        }
    return PackerRegistry.get(
        spec.copy(
            type=value_type,
            expression=(
                f"{spec.self_attrs_name}.{overridden_fn}({spec.expression})"
            ),
        )
    )


def get_overridden_serialization_method(
    spec: ValueSpec,
) -> Optional[Union[Callable, str, ExpressionWrapper]]:
    serialize_option = spec.field_ctx.metadata.get("serialize")
    if serialize_option is not None:
        return serialize_option
    checking_types = [spec.type, spec.origin_type]
    if spec.annotated_type:
        checking_types.insert(0, spec.annotated_type)
    for typ in checking_types:
        for strategy in spec.builder.iter_serialization_strategies(
            spec.field_ctx.metadata, typ
        ):
            if strategy is pass_through:
                return pass_through
            elif isinstance(strategy, dict):
                serialize_option = strategy.get("serialize")
            elif isinstance(strategy, SerializationStrategy):
                if strategy.__use_annotations__ or is_generic(type(strategy)):
                    return ExpressionWrapper(
                        _pack_with_annotated_serialization_strategy(
                            spec=spec,
                            strategy=strategy,
                        )
                    )
                else:
                    serialize_option = strategy.serialize
            if serialize_option is not None:
                return serialize_option


@register
def pack_type_with_overridden_serialization(
    spec: ValueSpec,
) -> Optional[Expression]:
    serialization_method = get_overridden_serialization_method(spec)
    if serialization_method is pass_through:
        return spec.expression
    elif isinstance(serialization_method, ExpressionWrapper):
        return serialization_method.expression
    elif callable(serialization_method):
        overridden_fn = f"__{spec.field_ctx.name}_serialize_{random_hex()}"
        setattr(spec.attrs, overridden_fn, staticmethod(serialization_method))
        return f"{spec.self_attrs_name}.{overridden_fn}({spec.expression})"


def _pack_annotated_serializable_type(
    spec: ValueSpec,
) -> Optional[Expression]:
    try:
        # noinspection PyProtectedMember
        # noinspection PyUnresolvedReferences
        value_type = get_function_return_annotation(
            spec.origin_type._serialize
        )
    except (KeyError, ValueError):
        raise UnserializableField(
            field_name=spec.field_ctx.name,
            field_type=spec.type,
            holder_class=spec.builder.cls,
            msg="Method _serialize must have return annotation",
        ) from None
    if is_self(value_type):
        return f"{spec.expression}._serialize()"
    if isinstance(value_type, ForwardRef):
        value_type = spec.builder.evaluate_forward_ref(
            value_type, spec.origin_type
        )
    value_type = substitute_type_params(
        value_type,
        resolve_type_params(spec.origin_type, get_args(spec.type))[
            spec.origin_type
        ],
    )
    return PackerRegistry.get(
        spec.copy(
            type=value_type,
            expression=f"{spec.expression}._serialize()",
        )
    )


@register
def pack_serializable_type(spec: ValueSpec) -> Optional[Expression]:
    try:
        if not issubclass(spec.origin_type, SerializableType):
            return None
    except TypeError:
        return None
    if spec.origin_type.__use_annotations__:
        return _pack_annotated_serializable_type(spec)
    else:
        return f"{spec.expression}._serialize()"


@register
def pack_generic_serializable_type(spec: ValueSpec) -> Optional[Expression]:
    with suppress(TypeError):
        if issubclass(spec.origin_type, GenericSerializableType):
            type_args = get_args(spec.type)
            spec.builder.add_type_modules(*type_args)
            type_arg_names = ", ".join(list(map(type_name, type_args)))
            return f"{spec.expression}._serialize([{type_arg_names}])"


@register
def pack_dataclass(spec: ValueSpec) -> Optional[Expression]:
    if is_dataclass(spec.origin_type):
        type_args = get_args(spec.type)
        method_name = spec.builder.get_pack_method_name(
            type_args, spec.builder.format_name
        )
        method_loc = spec.origin_type if spec.builder.is_nailed else spec.attrs
        if get_class_that_defines_method(
            method_name, method_loc
        ) != method_loc and (
            spec.origin_type != spec.builder.cls
            or spec.builder.get_pack_method_name(
                type_args=type_args,
                format_name=spec.builder.format_name,
                encoder=spec.builder.encoder,
            )
            != method_name
        ):
            builder = spec.builder.__class__(
                spec.origin_type,
                type_args,
                dialect=spec.builder.dialect,
                format_name=spec.builder.format_name,
                default_dialect=spec.builder.default_dialect,
                attrs=method_loc,
                attrs_registry=(
                    spec.attrs_registry if not spec.builder.is_nailed else None
                ),
            )
            builder.add_pack_method()
        flags = spec.builder.get_pack_method_flags(spec.type)
        if spec.builder.is_nailed:
            return f"{spec.expression}.{method_name}({flags})"
        else:
            cls_alias = clean_id(type_name(spec.origin_type))
            method_name_alias = f"{cls_alias}_{method_name}"
            spec.builder.ensure_object_imported(
                getattr(spec.attrs, method_name), method_name_alias
            )
            method_args = spec.expression
            return f"{method_name_alias}({method_args})"


@register
def pack_final(spec: ValueSpec) -> Optional[Expression]:
    if is_final(spec.type):
        return PackerRegistry.get(spec.copy(type=get_args(spec.type)[0]))


@register
def pack_any(spec: ValueSpec) -> Optional[Expression]:
    if spec.type is Any:
        return spec.expression


def pack_union(
    spec: ValueSpec, args: Tuple[Type, ...], prefix: str = "union"
) -> Expression:
    lines = CodeLines()
    method_name = (
        f"__pack_{prefix}_{spec.builder.cls.__name__}_{spec.field_ctx.name}__"
        f"{random_hex()}"
    )
    method_args = "self, value" if spec.builder.is_nailed else "value"
    default_kwargs = spec.builder.get_pack_method_default_flag_values()
    if default_kwargs:
        lines.append(f"def {method_name}({method_args}, {default_kwargs}):")
    else:
        lines.append(f"def {method_name}({method_args}):")
    packers: List[str] = []
    packer_arg_types: Dict[str, List[Type]] = {}
    for type_arg in args:
        packer = PackerRegistry.get(
            spec.copy(type=type_arg, expression="value")
        )
        if packer not in packers:
            if packer == "value":
                packers.insert(0, packer)
            else:
                packers.append(packer)
        packer_arg_types.setdefault(packer, []).append(type_arg)

    if len(packers) == 1 and packers[0] == "value":
        return spec.expression

    with lines.indent():
        for packer in packers:
            packer_arg_type_names = []
            for packer_arg_type in packer_arg_types[packer]:
                if is_generic(packer_arg_type):
                    packer_arg_type = get_type_origin(packer_arg_type)
                packer_arg_type_name = clean_id(type_name(packer_arg_type))
                spec.builder.ensure_object_imported(
                    packer_arg_type, packer_arg_type_name
                )
                if packer_arg_type_name not in packer_arg_type_names:
                    packer_arg_type_names.append(packer_arg_type_name)
            if len(packer_arg_type_names) > 1:
                packer_arg_type_check = (
                    f"in ({', '.join(packer_arg_type_names)})"
                )
            else:
                packer_arg_type_check = f"is {packer_arg_type_names[0]}"
            if packer == "value":
                with lines.indent(
                    f"if value.__class__ {packer_arg_type_check}:"
                ):
                    lines.append(f"return {packer}")
            else:
                with lines.indent("try:"):
                    lines.append(f"return {packer}")
                with lines.indent("except Exception:"):
                    lines.append("pass")
        field_type = spec.builder.get_type_name_identifier(
            typ=spec.type,
            resolved_type_params=spec.builder.get_field_resolved_type_params(
                spec.field_ctx.name
            ),
        )
        if spec.builder.is_nailed:
            lines.append(
                "raise InvalidFieldValue("
                f"'{spec.field_ctx.name}',{field_type},value,type(self))"
            )
        else:
            lines.append("raise ValueError(value)")
    lines.append(
        f"setattr({spec.cls_attrs_name}, '{method_name}', {method_name})"
    )
    if spec.builder.get_config().debug:
        print(f"{type_name(spec.builder.cls)}:")
        print(lines.as_text())
    exec(lines.as_text(), spec.builder.globals, spec.builder.__dict__)
    method_args = ", ".join(
        filter(None, (spec.expression, spec.builder.get_pack_method_flags()))
    )
    if spec.builder.is_nailed:
        return f"{spec.self_attrs_name}.{method_name}({method_args})"
    else:
        spec.builder.ensure_object_imported(
            getattr(spec.attrs, method_name), method_name
        )
        return f"{method_name}({method_args})"


def pack_literal(spec: ValueSpec) -> Expression:
    spec.builder.add_type_modules(spec.type)
    lines = CodeLines()
    method_name = (
        f"__pack_literal_{spec.builder.cls.__name__}_{spec.field_ctx.name}__"
        f"{random_hex()}"
    )
    method_args = "self, value" if spec.builder.is_nailed else "value"
    default_kwargs = spec.builder.get_pack_method_default_flag_values()
    if default_kwargs:
        lines.append(f"def {method_name}({method_args}, {default_kwargs}):")
    else:
        lines.append(f"def {method_name}({method_args}):")
    resolved_type_params = spec.builder.get_field_resolved_type_params(
        spec.field_ctx.name
    )
    with lines.indent():
        for literal_value in get_literal_values(spec.type):
            value_type = type(literal_value)
            packer = PackerRegistry.get(
                spec.copy(type=value_type, expression="value")
            )
            if isinstance(literal_value, enum.Enum):
                enum_type_name = spec.builder.get_type_name_identifier(
                    typ=value_type,
                    resolved_type_params=resolved_type_params,
                )
                with lines.indent(
                    f"if value == {enum_type_name}.{literal_value.name}:"
                ):
                    lines.append(f"return {packer}")
            elif isinstance(
                literal_value,
                (int, str, bytes, bool, NoneType),  # type: ignore
            ):
                with lines.indent(f"if value == {literal_value!r}:"):
                    lines.append(f"return {packer}")
        field_type = spec.builder.get_type_name_identifier(
            typ=spec.type,
            resolved_type_params=resolved_type_params,
        )
        if spec.builder.is_nailed:
            lines.append(
                f"raise InvalidFieldValue('{spec.field_ctx.name}',"
                f"{field_type},value,type(self))"
            )
        else:
            lines.append("raise ValueError(value)")
    lines.append(
        f"setattr({spec.cls_attrs_name}, '{method_name}', {method_name})"
    )
    if spec.builder.get_config().debug:
        print(f"{type_name(spec.builder.cls)}:")
        print(lines.as_text())
    exec(lines.as_text(), spec.builder.globals, spec.builder.__dict__)
    method_args = ", ".join(
        filter(None, (spec.expression, spec.builder.get_pack_method_flags()))
    )
    return f"{spec.self_attrs_name}.{method_name}({method_args})"


@register
def pack_special_typing_primitive(spec: ValueSpec) -> Optional[Expression]:
    if is_special_typing_primitive(spec.origin_type):
        if is_union(spec.type):
            resolved_type_params = spec.builder.get_field_resolved_type_params(
                spec.field_ctx.name
            )
            if is_optional(spec.type, resolved_type_params):
                arg = not_none_type_arg(
                    get_args(spec.type), resolved_type_params
                )
                pv = PackerRegistry.get(spec.copy(type=arg))
                return expr_or_maybe_none(spec, pv)
            else:
                return pack_union(spec, get_args(spec.type))
        elif spec.origin_type is typing.AnyStr:
            raise UnserializableDataError(
                "AnyStr is not supported by mashumaro"
            )
        elif is_type_var_any(spec.type):
            return spec.expression
        elif is_type_var(spec.type):
            constraints = getattr(spec.type, "__constraints__")
            if constraints:
                return pack_union(spec, constraints, "type_var")
            else:
                if type_var_has_default(spec.type):
                    bound = get_type_var_default(spec.type)
                else:
                    bound = getattr(spec.type, "__bound__")
                # act as if it was Optional[bound]
                pv = PackerRegistry.get(spec.copy(type=bound))
                return expr_or_maybe_none(spec, pv)
        elif is_new_type(spec.type):
            return PackerRegistry.get(spec.copy(type=spec.type.__supertype__))
        elif is_literal(spec.type):
            return pack_literal(spec)
        elif spec.type is typing_extensions.LiteralString:
            return PackerRegistry.get(spec.copy(type=str))
        elif is_self(spec.type):
            method_name = spec.builder.get_pack_method_name(
                format_name=spec.builder.format_name
            )
            method_loc = (
                spec.builder.cls if spec.builder.is_nailed else spec.attrs
            )
            if (
                get_class_that_defines_method(method_name, method_loc)
                != method_loc
                # not hasattr(self.cls, method_name)
                and spec.builder.get_pack_method_name(
                    format_name=spec.builder.format_name,
                    encoder=spec.builder.encoder,
                )
                != method_name
            ):
                builder = spec.builder.__class__(
                    spec.builder.cls,
                    dialect=spec.builder.dialect,
                    format_name=spec.builder.format_name,
                    default_dialect=spec.builder.default_dialect,
                    attrs=method_loc,
                    attrs_registry=(
                        spec.attrs_registry
                        if not spec.builder.is_nailed
                        else None
                    ),
                )
                builder.add_pack_method()
            flags = spec.builder.get_pack_method_flags(spec.builder.cls)
            if spec.builder.is_nailed:
                return f"{spec.expression}.{method_name}({flags})"
            else:
                method_args = spec.expression
                return f"_cls.{method_name}({method_args})"
        elif is_required(spec.type) or is_not_required(spec.type):
            return PackerRegistry.get(spec.copy(type=get_args(spec.type)[0]))
        elif is_unpack(spec.type):
            packer = PackerRegistry.get(spec.copy(type=get_args(spec.type)[0]))
            return f"*{packer}"
        elif is_type_var_tuple(spec.type):
            return PackerRegistry.get(spec.copy(type=Tuple[Any, ...]))
        elif isinstance(spec.type, ForwardRef):
            evaluated = spec.builder.evaluate_forward_ref(
                spec.type, spec.owner
            )
            if evaluated is not None:
                return PackerRegistry.get(spec.copy(type=evaluated))
        elif is_type_alias_type(spec.type):
            return PackerRegistry.get(spec.copy(type=spec.type.__value__))
        raise UnserializableDataError(
            f"{spec.type} as a field type is not supported by mashumaro"
        )


@register
def pack_number_and_bool_and_none(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type in (int, float, bool, NoneType, None):
        return spec.expression


@register
def pack_date_objects(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type in (datetime.datetime, datetime.date, datetime.time):
        return f"{spec.expression}.isoformat()"


@register
def pack_timedelta(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is datetime.timedelta:
        return f"{spec.expression}.total_seconds()"


@register
def pack_timezone(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is datetime.timezone:
        return f"{spec.expression}.tzname(None)"


@register
def pack_zone_info(spec: ValueSpec) -> Optional[Expression]:
    if PY_39_MIN and spec.origin_type is zoneinfo.ZoneInfo:
        return f"str({spec.expression})"


@register
def pack_uuid(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is uuid.UUID:
        return f"str({spec.expression})"


@register
def pack_ipaddress(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type in (
        ipaddress.IPv4Address,
        ipaddress.IPv6Address,
        ipaddress.IPv4Network,
        ipaddress.IPv6Network,
        ipaddress.IPv4Interface,
        ipaddress.IPv6Interface,
    ):
        return f"str({spec.expression})"


@register
def pack_decimal(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is Decimal:
        return f"str({spec.expression})"


@register
def pack_fraction(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is Fraction:
        return f"str({spec.expression})"


def pack_tuple(spec: ValueSpec, args: Tuple[Type, ...]) -> Expression:
    if not args:
        if spec.type in (Tuple, tuple):
            args = [typing.Any, ...]  # type: ignore
        else:
            return "[]"
    elif len(args) == 1 and args[0] == ():
        if not PY_311_MIN:
            return "[]"
    if len(args) == 2 and args[1] is Ellipsis:
        packer = PackerRegistry.get(
            spec.copy(type=args[0], expression="value", could_be_none=True)
        )
        return f"[{packer} for value in {spec.expression}]"
    else:
        arg_indexes: List[Union[int, Tuple[int, Union[int, None]]]] = []
        unpack_idx: Optional[int] = None
        for arg_idx, type_arg in enumerate(args):
            if is_unpack(type_arg):
                if unpack_idx is not None:
                    raise TypeError(
                        "Multiple unpacks are disallowed within a single type "
                        f"parameter list for {type_name(spec.type)}"
                    )
                unpack_idx = arg_idx
                if len(args) == 1:
                    arg_indexes.append((arg_idx, None))
                elif arg_idx < len(args) - 1:
                    arg_indexes.append((arg_idx, arg_idx + 1 - len(args)))
                else:
                    arg_indexes.append((arg_idx, None))
            else:
                if unpack_idx is None:
                    arg_indexes.append(arg_idx)
                else:
                    arg_indexes.append(arg_idx - len(args))
        packers: List[Expression] = []
        for _idx, _arg_idx in enumerate(arg_indexes):
            if isinstance(_arg_idx, tuple):
                p_expr = f"{spec.expression}[{_arg_idx[0]}:{_arg_idx[1]}]"
            else:
                p_expr = f"{spec.expression}[{_arg_idx}]"
            packer = PackerRegistry.get(
                spec.copy(
                    type=args[_idx],
                    expression=p_expr,
                    could_be_none=True,
                )
            )
            if packer != "*[]":
                packers.append(packer)
        return f"[{', '.join(packers)}]"


def pack_named_tuple(spec: ValueSpec) -> Expression:
    resolved = resolve_type_params(spec.origin_type, get_args(spec.type))[
        spec.origin_type
    ]
    annotations = {
        k: resolved.get(v, v)
        for k, v in getattr(spec.origin_type, "__annotations__", {}).items()
    }
    fields = getattr(spec.type, "_fields", ())
    packers = []
    as_dict = spec.builder.get_dialect_or_config_option(
        "namedtuple_as_dict", False
    )
    serialize_option = get_overridden_serialization_method(spec)
    if serialize_option is not None:
        if serialize_option == "as_dict":
            as_dict = True
        elif serialize_option == "as_list":
            as_dict = False
        else:
            raise UnsupportedSerializationEngine(
                field_name=spec.field_ctx.name,
                field_type=spec.type,
                holder_class=spec.builder.cls,
                engine=serialize_option,
            )
    for idx, field in enumerate(fields):
        packer = PackerRegistry.get(
            spec.copy(
                type=annotations.get(field, typing.Any),
                expression=f"{spec.expression}[{idx}]",
                could_be_none=True,
            )
        )
        packers.append(packer)
    if as_dict:
        kv = (f"'{key}': {value}" for key, value in zip(fields, packers))
        return f"{{{', '.join(kv)}}}"
    else:
        return f"[{', '.join(packers)}]"


def pack_typed_dict(spec: ValueSpec) -> Expression:
    resolved = resolve_type_params(spec.origin_type, get_args(spec.type))[
        spec.origin_type
    ]
    annotations = {
        k: resolved.get(v, v)
        for k, v in spec.origin_type.__annotations__.items()
    }
    all_keys = list(annotations.keys())
    required_keys = getattr(spec.type, "__required_keys__", all_keys)
    optional_keys = getattr(spec.type, "__optional_keys__", [])
    lines = CodeLines()
    method_name = (
        f"__pack_typed_dict_{spec.builder.cls.__name__}_"
        f"{spec.field_ctx.name}__{random_hex()}"
    )
    method_args = "self, value" if spec.builder.is_nailed else "value"
    default_kwargs = spec.builder.get_pack_method_default_flag_values()
    if default_kwargs:
        lines.append(f"def {method_name}({method_args}, {default_kwargs}):")
    else:
        lines.append(f"def {method_name}({method_args}):")
    with lines.indent():
        lines.append("d = {}")
        for key in sorted(required_keys, key=all_keys.index):
            packer = PackerRegistry.get(
                spec.copy(
                    type=annotations[key],
                    expression=f"value['{key}']",
                    could_be_none=True,
                    owner=spec.type,
                )
            )
            lines.append(f"d['{key}'] = {packer}")
        for key in sorted(optional_keys, key=all_keys.index):
            lines.append(f"key_value = value.get('{key}', MISSING)")
            with lines.indent("if key_value is not MISSING:"):
                packer = PackerRegistry.get(
                    spec.copy(
                        type=annotations[key],
                        expression="key_value",
                        could_be_none=True,
                        owner=spec.type,
                    )
                )
                lines.append(f"d['{key}'] = {packer}")
        lines.append("return d")
    lines.append(
        f"setattr({spec.cls_attrs_name}, '{method_name}', {method_name})"
    )
    if spec.builder.get_config().debug:
        print(f"{type_name(spec.builder.cls)}:")
        print(lines.as_text())
    exec(lines.as_text(), spec.builder.globals, spec.builder.__dict__)
    method_args = ", ".join(
        filter(None, (spec.expression, spec.builder.get_pack_method_flags()))
    )
    return f"{spec.self_attrs_name}.{method_name}({method_args})"


@register
def pack_collection(spec: ValueSpec) -> Optional[Expression]:
    if not issubclass(spec.origin_type, typing.Collection):
        return None
    elif issubclass(spec.origin_type, enum.Enum):
        return None

    args = get_args(spec.type)

    def inner_expr(
        arg_num: int = 0, v_name: str = "value", v_type: Optional[Type] = None
    ) -> Expression:
        if v_type:
            return PackerRegistry.get(
                spec.copy(type=v_type, expression=v_name)
            )
        else:
            if args and len(args) > arg_num:
                type_arg: Any = args[arg_num]
            else:
                type_arg = Any
            return PackerRegistry.get(
                spec.copy(
                    type=type_arg,
                    expression=v_name,
                    could_be_none=True,
                    field_ctx=spec.field_ctx.copy(metadata={}),
                )
            )

    def _make_sequence_expression(ie: Expression) -> Expression:
        if ie == "value":
            if spec.origin_type in spec.no_copy_collections:
                return spec.expression
            elif spec.origin_type is list:
                return f"{spec.expression}.copy()"
        return f"[{ie} for value in {spec.expression}]"

    def _make_mapping_expression(ke: Expression, ve: Expression) -> Expression:
        if ke == "key" and ve == "value":
            if spec.origin_type in spec.no_copy_collections:
                return spec.expression
            elif spec.origin_type is dict:
                return f"{spec.expression}.copy()"
        return f"{{{ke}: {ve} for key, value in {spec.expression}.items()}}"

    if issubclass(spec.origin_type, typing.ByteString):  # type: ignore
        spec.builder.ensure_object_imported(encodebytes)
        return f"encodebytes({spec.expression}).decode()"
    elif issubclass(spec.origin_type, str):
        return spec.expression
    elif issubclass(spec.origin_type, Tuple):  # type: ignore
        if is_named_tuple(spec.origin_type):
            return pack_named_tuple(spec)
        elif ensure_generic_collection(spec):
            return pack_tuple(spec, args)
    elif ensure_generic_collection_subclass(
        spec, typing.List, typing.Deque, typing.AbstractSet
    ):
        ie = inner_expr()
        return _make_sequence_expression(ie)
    elif ensure_generic_mapping(spec, args, typing.ChainMap):
        ke = inner_expr(0, "key")
        ve = inner_expr(1)
        return (
            f"[{{{ke}: {ve} for key, value in m.items()}} "
            f"for m in {spec.expression}.maps]"
        )
    elif ensure_generic_mapping(spec, args, typing.OrderedDict):
        ke = inner_expr(0, "key")
        ve = inner_expr(1)
        return _make_mapping_expression(ke, ve)
    elif ensure_generic_mapping(spec, args, typing.Counter):
        ke = inner_expr(0, "key")
        ve = inner_expr(1, v_type=int)
        return _make_mapping_expression(ke, ve)
    elif is_typed_dict(spec.origin_type):
        return pack_typed_dict(spec)
    elif ensure_generic_mapping(spec, args, typing.Mapping):
        ke = inner_expr(0, "key")
        ve = inner_expr(1)
        return _make_mapping_expression(ke, ve)
    elif ensure_generic_collection_subclass(spec, typing.Sequence):
        ie = inner_expr()
        return _make_sequence_expression(ie)


@register
def pack_pathlike(spec: ValueSpec) -> Optional[Expression]:
    if issubclass(spec.origin_type, os.PathLike):
        return f"{spec.expression}.__fspath__()"


@register
def pack_enum(spec: ValueSpec) -> Optional[Expression]:
    if issubclass(spec.origin_type, enum.Enum):
        return f"{spec.expression}.value"
