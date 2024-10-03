import collections
import collections.abc
import datetime
import enum
import ipaddress
import os
import pathlib
import types
import typing
import uuid
from abc import ABC
from base64 import decodebytes
from contextlib import suppress
from dataclasses import is_dataclass
from decimal import Decimal
from fractions import Fraction
from typing import (
    Any,
    Callable,
    ForwardRef,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)

import typing_extensions

from mashumaro.core.const import PY_39_MIN, PY_311_MIN
from mashumaro.core.helpers import parse_timezone
from mashumaro.core.meta.code.lines import CodeLines
from mashumaro.core.meta.helpers import (
    get_args,
    get_class_that_defines_method,
    get_function_arg_annotation,
    get_literal_values,
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
    iter_all_subclasses,
    not_none_type_arg,
    resolve_type_params,
    substitute_type_params,
    type_name,
    type_var_has_default,
)
from mashumaro.core.meta.types.common import (
    AbstractMethodBuilder,
    AttrsHolder,
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
    ThirdPartyModuleNotFoundError,
    UnserializableDataError,
    UnserializableField,
    UnsupportedDeserializationEngine,
)
from mashumaro.helper import pass_through
from mashumaro.types import (
    Discriminator,
    GenericSerializableType,
    SerializableType,
    SerializationStrategy,
)

if PY_39_MIN:
    import zoneinfo

try:
    import ciso8601
except ImportError:  # pragma: no cover
    ciso8601: Optional[types.ModuleType] = None  # type: ignore
try:
    import pendulum
except ImportError:  # pragma: no cover
    pendulum: Optional[types.ModuleType] = None  # type: ignore


__all__ = ["UnpackerRegistry", "SubtypeUnpackerBuilder"]


UnpackerRegistry = Registry()
register = UnpackerRegistry.register


class AbstractUnpackerBuilder(AbstractMethodBuilder, ABC):
    def _generate_method_name(self, spec: ValueSpec) -> str:
        prefix = self.get_method_prefix()
        if prefix:
            prefix = f"{prefix}_"
        if spec.field_ctx.name:
            suffix = f"_{spec.field_ctx.name}"
        else:
            suffix = ""
        return (
            f"__unpack_{prefix}{spec.builder.cls.__name__}{suffix}"
            f"__{random_hex()}"
        )

    def _add_definition(self, spec: ValueSpec, lines: CodeLines) -> str:
        method_name = self._generate_method_name(spec)
        method_args = self._generate_method_args(spec)
        if spec.builder.is_nailed:
            lines.append("@classmethod")
        lines.append(f"def {method_name}({method_args}):")
        return method_name

    def _get_extra_method_args(self) -> List[str]:
        return []

    def _generate_method_args(self, spec: ValueSpec) -> str:
        default_kwargs = spec.builder.get_unpack_method_default_flag_values()
        extra_args = self._get_extra_method_args()
        if extra_args:
            extra_args_str = f", {', '.join(extra_args)}"
        else:
            extra_args_str = ""
        if spec.builder.is_nailed:
            first_args = "cls, value"
        else:
            first_args = "value"
        if default_kwargs:
            return f"{first_args}{extra_args_str}, {default_kwargs}"
        else:  # pragma: no cover
            # we shouldn't be here because there will be default_kwargs
            return f"{first_args}{extra_args_str}"

    def _get_call_expr(self, spec: ValueSpec, method_name: str) -> str:
        method_args = ", ".join(
            filter(
                None, (spec.expression, spec.builder.get_unpack_method_flags())
            )
        )
        return f"{spec.cls_attrs_name}.{method_name}({method_args})"


class UnionUnpackerBuilder(AbstractUnpackerBuilder):
    def __init__(self, args: Tuple[Type, ...]):
        self.union_args = args

    def get_method_prefix(self) -> str:
        return "union"

    def _add_body(self, spec: ValueSpec, lines: CodeLines) -> None:
        ambiguous_unpacker_types = []
        for type_arg in self.union_args:
            unpacker = UnpackerRegistry.get(
                spec.copy(type=type_arg, expression="value")
            )
            if type_arg in (bool, str) and unpacker == "value":
                ambiguous_unpacker_types.append(type_arg)
            with lines.indent("try:"):
                lines.append(f"return {unpacker}")
            lines.append("except Exception: pass")
        # if len(ambiguous_unpacker_types) >= 2:
        #     warnings.warn(
        #         f"{type_name(spec.builder.cls)}.{spec.field_ctx.name} "
        #         f"({type_name(spec.type)}): "
        #         "In the next release, data marked with Union type "
        #         "containing 'str' and 'bool' will be coerced to the value "
        #         "of the type specified first instead of passing it as is"
        #     )
        field_type = spec.builder.get_type_name_identifier(
            typ=spec.type,
            resolved_type_params=spec.builder.get_field_resolved_type_params(
                spec.field_ctx.name
            ),
        )
        if spec.builder.is_nailed:
            lines.append(
                "raise InvalidFieldValue("
                f"'{spec.field_ctx.name}',{field_type},value,cls)"
            )
        else:
            lines.append("raise ValueError(value)")


class TypeVarUnpackerBuilder(UnionUnpackerBuilder):
    def get_method_prefix(self) -> str:
        return "type_var"


class LiteralUnpackerBuilder(AbstractUnpackerBuilder):
    def _before_build(self, spec: ValueSpec) -> None:
        spec.builder.add_type_modules(spec.type)

    def get_method_prefix(self) -> str:
        return "literal"

    def _add_body(self, spec: ValueSpec, lines: CodeLines) -> None:
        for literal_value in get_literal_values(spec.type):
            if isinstance(literal_value, enum.Enum):
                lit_type = type(literal_value)
                enum_type_name = spec.builder.get_type_name_identifier(
                    lit_type
                )
                with lines.indent(
                    f"if value == {enum_type_name}.{literal_value.name}.value:"
                ):
                    lines.append(
                        f"return {enum_type_name}.{literal_value.name}"
                    )
            elif isinstance(literal_value, bytes):
                unpacker = UnpackerRegistry.get(
                    spec.copy(type=bytes, expression="value")
                )
                with lines.indent("try:"):
                    with lines.indent(f"if {unpacker} == {literal_value!r}:"):
                        lines.append(f"return {literal_value!r}")
                lines.append("except Exception: pass")
            elif isinstance(
                literal_value,
                (int, str, bool, NoneType),  # type: ignore
            ):
                with lines.indent(f"if value == {literal_value!r}:"):
                    lines.append(f"return {literal_value!r}")
        lines.append("raise ValueError(value)")


class DiscriminatedUnionUnpackerBuilder(AbstractUnpackerBuilder):
    def __init__(
        self,
        discriminator: Discriminator,
        base_variants: Optional[Tuple[Type, ...]] = None,
    ):
        self.discriminator = discriminator
        self.base_variants = base_variants or tuple()
        self._variants_attr: Optional[str] = None

    def get_method_prefix(self) -> str:
        return ""

    def _get_extra_method_args(self) -> List[str]:
        return ["_dialect", "_default_dialect"]

    def _get_variants_attr(self, spec: ValueSpec) -> str:
        if self._variants_attr is None:
            self._variants_attr = (
                f"__mashumaro_{spec.field_ctx.name}_variants_{random_hex()}__"
            )
        return self._variants_attr

    def _get_variants_map(self, spec: ValueSpec) -> str:
        variants_attr = self._get_variants_attr(spec)
        if spec.builder.is_nailed:
            typ_name = spec.builder.get_type_name_identifier(spec.builder.cls)
            return f"{typ_name}.{variants_attr}"
        else:
            return f"{spec.cls_attrs_name}.{variants_attr}"

    def _get_variant_names(self, spec: ValueSpec) -> List[str]:
        base_variants = self.base_variants or (spec.origin_type,)
        variant_names: List[str] = []
        if self.discriminator.include_subtypes:
            spec.builder.ensure_object_imported(iter_all_subclasses)
            variant_names.extend(
                f"*iter_all_subclasses("
                f"{spec.builder.get_type_name_identifier(base_variant)})"
                for base_variant in base_variants
            )
        if self.discriminator.include_supertypes:
            variant_names.extend(
                map(spec.builder.get_type_name_identifier, base_variants)
            )
        return variant_names

    def _get_variant_names_iterable(self, spec: ValueSpec) -> str:
        variant_names = self._get_variant_names(spec)
        if len(variant_names) == 1:
            if variant_names[0].startswith("*"):
                return variant_names[0][1:]
            else:
                return f"[{variant_names[0]}]"
        return f'({", ".join(variant_names)})'

    @staticmethod
    def _get_variants_attr_holder(spec: ValueSpec) -> Type:
        return spec.attrs

    @staticmethod
    def _get_variant_method_call(method_name: str, spec: ValueSpec) -> str:
        method_flags = spec.builder.get_unpack_method_flags()
        if method_flags:
            return f"{method_name}(value, {method_flags})"
        else:
            return f"{method_name}(value)"

    def _add_body(self, spec: ValueSpec, lines: CodeLines) -> None:
        discriminator = self.discriminator

        variants_attr = self._get_variants_attr(spec)
        variants_map = self._get_variants_map(spec)
        variants_attr_holder = self._get_variants_attr_holder(spec)
        variants = self._get_variant_names_iterable(spec)
        variants_type_expr = spec.builder.get_type_name_identifier(spec.type)

        if variants_attr not in variants_attr_holder.__dict__:
            setattr(variants_attr_holder, variants_attr, {})
        variant_method_name = spec.builder.get_unpack_method_name(
            format_name=spec.builder.format_name
        )
        variant_method_call = self._get_variant_method_call(
            variant_method_name, spec
        )
        if discriminator.variant_tagger_fn:
            spec.builder.ensure_object_imported(
                discriminator.variant_tagger_fn, "variant_tagger_fn"
            )
            variant_tagger_expr = "variant_tagger_fn(variant)"
        else:
            variant_tagger_expr = f"variant.__dict__['{discriminator.field}']"

        if spec.builder.dialect:
            spec.builder.ensure_object_imported(
                spec.builder.dialect,
                clean_id(type_name(spec.builder.dialect)),
            )
        if spec.builder.default_dialect:
            spec.builder.ensure_object_imported(
                spec.builder.default_dialect,
                clean_id(type_name(spec.builder.default_dialect)),
            )

        if discriminator.field:
            chosen_cls = f"{variants_map}[discriminator]"
            with lines.indent("try:"):
                lines.append(f"discriminator = value['{discriminator.field}']")
            with lines.indent("except KeyError:"):
                lines.append(
                    f"raise MissingDiscriminatorError('{discriminator.field}')"
                    " from None"
                )
            with lines.indent("try:"):
                if spec.builder.is_nailed:
                    lines.append(f"return {chosen_cls}.{variant_method_call}")
                else:
                    lines.append(
                        f"return {spec.attrs_registry_name}"
                        f"[{chosen_cls}].{variant_method_call}"
                    )
            with lines.indent("except (KeyError, AttributeError):"):
                lines.append(f"variants_map = {variants_map}")
                with lines.indent(f"for variant in {variants}:"):
                    if discriminator.variant_tagger_fn is not None:
                        self._add_register_variant_tags(
                            lines, variant_tagger_expr
                        )
                    else:
                        with lines.indent("try:"):
                            self._add_register_variant_tags(
                                lines, variant_tagger_expr
                            )
                        with lines.indent("except KeyError:"):
                            lines.append("continue")
                    self._add_build_variant_unpacker(
                        spec, lines, variant_method_name, variant_method_call
                    )
                with lines.indent("try:"):
                    if spec.builder.is_nailed:
                        lines.append(
                            "return variants_map[discriminator]"
                            f".{variant_method_call}"
                        )
                    else:
                        lines.append(
                            f"return {spec.attrs_registry_name}["
                            "variants_map[discriminator]]"
                            f".{variant_method_call}"
                        )
                with lines.indent("except KeyError:"):
                    lines.append(
                        "raise SuitableVariantNotFoundError("
                        f"{variants_type_expr}, '{discriminator.field}', "
                        "discriminator) from None"
                    )
        else:
            with lines.indent(f"for variant in {variants}:"):
                with lines.indent("try:"):
                    if spec.builder.is_nailed:
                        lines.append(f"return variant.{variant_method_call}")
                    else:
                        lines.append(
                            f"return {spec.attrs_registry_name}"
                            f"[variant].{variant_method_call}"
                        )
                if spec.builder.is_nailed:
                    exc_to_catch = "AttributeError"
                else:
                    exc_to_catch = "(KeyError, AttributeError)"
                with lines.indent(f"except {exc_to_catch}:"):
                    self._add_build_variant_unpacker(
                        spec, lines, variant_method_name, variant_method_call
                    )
                lines.append("except Exception: pass")
            lines.append(
                f"raise SuitableVariantNotFoundError({variants_type_expr}) "
                "from None"
            )

    def _get_call_expr(self, spec: ValueSpec, method_name: str) -> str:
        method_args = ", ".join(
            filter(
                None,
                (
                    spec.expression,
                    clean_id(type_name(spec.builder.dialect)),
                    clean_id(type_name(spec.builder.default_dialect)),
                    spec.builder.get_unpack_method_flags(),
                ),
            )
        )
        return f"{spec.cls_attrs_name}.{method_name}({method_args})"

    def _add_build_variant_unpacker(
        self,
        spec: ValueSpec,
        lines: CodeLines,
        variant_method_name: str,
        variant_method_call: str,
    ) -> None:
        if spec.builder.is_nailed:
            spec.builder.ensure_object_imported(get_class_that_defines_method)
            lines.append(
                "if get_class_that_defines_method("
                f"'{variant_method_name}',variant) != variant:"
            )
            with lines.indent():
                spec.builder.ensure_object_imported(spec.builder.__class__)
                lines.append(
                    "CodeBuilder(variant, "
                    "dialect=_dialect, "
                    f"format_name={repr(spec.builder.format_name)}, "
                    "default_dialect=_default_dialect)"
                    ".add_unpack_method()"
                )
                if not self.discriminator.field:
                    with lines.indent("try:"):
                        lines.append(f"return variant.{variant_method_call}")
                    lines.append("except Exception: pass")
        else:
            spec.builder.ensure_object_imported(AttrsHolder)
            attrs = f"attrs_{random_hex()}"
            lines.append(f"{attrs} = AttrsHolder('{attrs}')")
            lines.append(f"{spec.attrs_registry_name}[variant] = {attrs}")
            lines.append(
                "CodeBuilder(variant, "
                "dialect=_dialect, "
                f"format_name={repr(spec.builder.format_name)}, "
                "default_dialect=_default_dialect,"
                f"attrs={attrs},"
                f"attrs_registry={spec.attrs_registry_name})"
                ".add_unpack_method()"
            )
            if not self.discriminator.field:
                with lines.indent("try:"):
                    lines.append(f"return {attrs}.{variant_method_call}")
                lines.append("except Exception: pass")

    def _add_register_variant_tags(
        self, lines: CodeLines, variant_tagger_expr: str
    ) -> None:
        if self.discriminator.variant_tagger_fn:
            lines.append(f"variant_tags = {variant_tagger_expr}")
            with lines.indent("if type(variant_tags) is list:"):
                with lines.indent("for varint_tag in variant_tags:"):
                    lines.append("variants_map[varint_tag] = variant")
            with lines.indent("else:"):
                lines.append("variants_map[variant_tags] = variant")
        else:
            lines.append(f"variants_map[{variant_tagger_expr}] = variant")


class SubtypeUnpackerBuilder(DiscriminatedUnionUnpackerBuilder):
    def _get_variants_attr(self, spec: ValueSpec) -> str:
        if self._variants_attr is None:
            assert self.discriminator.include_subtypes
            self._variants_attr = "__mashumaro_subtype_variants__"
        return self._variants_attr


def _unpack_with_annotated_serialization_strategy(
    spec: ValueSpec,
    strategy: SerializationStrategy,
) -> Expression:
    strategy_type = type(strategy)
    try:
        value_type: Union[Type, Any] = get_function_arg_annotation(
            strategy.deserialize, arg_pos=0
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
    overridden_fn = f"__{spec.field_ctx.name}_deserialize_{random_hex()}"
    setattr(spec.attrs, overridden_fn, strategy.deserialize)
    new_spec = spec.copy(type=value_type)
    field_metadata = new_spec.field_ctx.metadata
    if field_metadata.get("serialization_strategy") is strategy:
        new_spec.field_ctx.metadata = {
            k: v
            for k, v in field_metadata.items()
            if k != "serialization_strategy"
        }
    unpacker = UnpackerRegistry.get(new_spec)
    return f"{spec.cls_attrs_name}.{overridden_fn}({unpacker})"


def get_overridden_deserialization_method(
    spec: ValueSpec,
) -> Optional[Union[Callable, str, ExpressionWrapper]]:
    deserialize_option = spec.field_ctx.metadata.get("deserialize")
    if deserialize_option is not None:
        return deserialize_option
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
                deserialize_option = strategy.get("deserialize")
            elif isinstance(strategy, SerializationStrategy):
                if strategy.__use_annotations__ or is_generic(type(strategy)):
                    return ExpressionWrapper(
                        _unpack_with_annotated_serialization_strategy(
                            spec=spec,
                            strategy=strategy,
                        )
                    )
                deserialize_option = strategy.deserialize
            if deserialize_option is not None:
                return deserialize_option


@register
def unpack_type_with_overridden_deserialization(
    spec: ValueSpec,
) -> Optional[Expression]:
    deserialization_method = get_overridden_deserialization_method(spec)
    if deserialization_method is pass_through:
        return spec.expression
    elif isinstance(deserialization_method, ExpressionWrapper):
        return deserialization_method.expression
    elif callable(deserialization_method):
        overridden_fn = f"__{spec.field_ctx.name}_deserialize_{random_hex()}"
        setattr(spec.attrs, overridden_fn, deserialization_method)
        return f"{spec.cls_attrs_name}.{overridden_fn}({spec.expression})"


def _unpack_annotated_serializable_type(
    spec: ValueSpec,
) -> Optional[Expression]:
    try:
        # noinspection PyProtectedMember
        # noinspection PyUnresolvedReferences
        value_type = get_function_arg_annotation(
            spec.origin_type._deserialize, arg_pos=0
        )
    except (KeyError, ValueError):
        raise UnserializableField(
            field_name=spec.field_ctx.name,
            field_type=spec.type,
            holder_class=spec.builder.cls,
            msg='Method _deserialize must have annotated "value" argument',
        ) from None
    if is_self(value_type):
        return (
            f"{spec.builder.get_type_name_identifier(spec.type)}"
            f"._deserialize({spec.expression})"
        )
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
    unpacker = UnpackerRegistry.get(spec.copy(type=value_type))
    field_type = spec.builder.get_type_name_identifier(spec.type)
    return f"{field_type}._deserialize({unpacker})"


@register
def unpack_serializable_type(spec: ValueSpec) -> Optional[Expression]:
    try:
        if not issubclass(spec.origin_type, SerializableType):
            return None
    except TypeError:
        return None
    if spec.origin_type.__use_annotations__:
        return _unpack_annotated_serializable_type(spec)
    else:
        field_type = spec.builder.get_type_name_identifier(spec.type)
        return f"{field_type}._deserialize({spec.expression})"


@register
def unpack_generic_serializable_type(spec: ValueSpec) -> Optional[Expression]:
    with suppress(TypeError):
        if issubclass(spec.origin_type, GenericSerializableType):
            type_arg_names = ", ".join(
                list(map(type_name, get_args(spec.type)))
            )
            field_type = spec.builder.get_type_name_identifier(
                spec.origin_type
            )
            return (
                f"{field_type}._deserialize({spec.expression}, "
                f"[{type_arg_names}])"
            )


@register
def unpack_dataclass(spec: ValueSpec) -> Optional[Expression]:
    if is_dataclass(spec.origin_type):
        for annotation in spec.annotations:
            if isinstance(annotation, Discriminator):
                return DiscriminatedUnionUnpackerBuilder(annotation).build(
                    spec
                )
        type_args = get_args(spec.type)
        method_name = spec.builder.get_unpack_method_name(
            type_args, spec.builder.format_name
        )
        method_loc = spec.origin_type if spec.builder.is_nailed else spec.attrs
        if get_class_that_defines_method(
            method_name, method_loc
        ) != method_loc and (
            spec.origin_type != spec.builder.cls
            or spec.builder.get_unpack_method_name(
                type_args=type_args,
                format_name=spec.builder.format_name,
                decoder=spec.builder.decoder,
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
            builder.add_unpack_method()
        method_args = ", ".join(
            filter(
                None,
                (
                    spec.expression,
                    spec.builder.get_unpack_method_flags(spec.type),
                ),
            )
        )
        cls_alias = clean_id(type_name(spec.origin_type))
        if spec.builder.is_nailed:
            spec.builder.ensure_object_imported(spec.origin_type, cls_alias)
            return f"{cls_alias}.{method_name}({method_args})"
        else:
            method_name_alias = f"{cls_alias}_{method_name}"
            spec.builder.ensure_object_imported(
                getattr(spec.attrs, method_name),
                method_name_alias,
            )
            return f"{method_name_alias}({method_args})"


@register
def unpack_final(spec: ValueSpec) -> Optional[Expression]:
    if is_final(spec.type):
        return UnpackerRegistry.get(spec.copy(type=get_args(spec.type)[0]))


@register
def unpack_any(spec: ValueSpec) -> Optional[Expression]:
    if spec.type is Any:
        return spec.expression


@register
def unpack_special_typing_primitive(spec: ValueSpec) -> Optional[Expression]:
    if is_special_typing_primitive(spec.origin_type):
        if is_union(spec.type):
            resolved_type_params = spec.builder.get_field_resolved_type_params(
                spec.field_ctx.name
            )
            if is_optional(spec.type, resolved_type_params):
                arg = not_none_type_arg(
                    get_args(spec.type), resolved_type_params
                )
                uv = UnpackerRegistry.get(spec.copy(type=arg))
                return expr_or_maybe_none(spec, uv)
            else:
                union_args = get_args(spec.type)
                for annotation in spec.annotations:
                    if isinstance(annotation, Discriminator):
                        return DiscriminatedUnionUnpackerBuilder(
                            annotation, union_args
                        ).build(spec)
                return UnionUnpackerBuilder(union_args).build(spec)
        elif spec.origin_type is typing.AnyStr:
            raise UnserializableDataError(
                "AnyStr is not supported by mashumaro"
            )
        elif is_type_var_any(spec.type):
            return spec.expression
        elif is_type_var(spec.type):
            constraints = getattr(spec.type, "__constraints__")
            if constraints:
                return TypeVarUnpackerBuilder(constraints).build(spec)
            else:
                if type_var_has_default(spec.type):
                    bound = get_type_var_default(spec.type)
                else:
                    bound = getattr(spec.type, "__bound__")
                # act as if it was Optional[bound]
                uv = UnpackerRegistry.get(spec.copy(type=bound))
                return expr_or_maybe_none(spec, uv)
        elif is_new_type(spec.type):
            return UnpackerRegistry.get(
                spec.copy(type=spec.type.__supertype__)
            )
        elif is_literal(spec.type):
            return LiteralUnpackerBuilder().build(spec)
        elif spec.type is typing_extensions.LiteralString:
            return UnpackerRegistry.get(spec.copy(type=str))
        elif is_self(spec.type):
            method_name = spec.builder.get_unpack_method_name(
                format_name=spec.builder.format_name
            )
            method_loc = (
                spec.builder.cls if spec.builder.is_nailed else spec.attrs
            )
            if (
                get_class_that_defines_method(method_name, method_loc)
                != method_loc
                # not hasattr(spec.builder.cls, method_name)
                and spec.builder.get_unpack_method_name(
                    format_name=spec.builder.format_name,
                    decoder=spec.builder.decoder,
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
                builder.add_unpack_method()
            method_args = ", ".join(
                filter(
                    None,
                    (
                        spec.expression,
                        spec.builder.get_unpack_method_flags(spec.builder.cls),
                    ),
                )
            )
            if spec.builder.is_nailed:
                spec.builder.add_type_modules(spec.builder.cls)
                self_cls_name = spec.builder.get_type_name_identifier(
                    spec.builder.cls
                )
                return f"{self_cls_name}.{method_name}({method_args})"
            else:
                return f"_cls.{method_name}({method_args})"
        elif is_required(spec.type) or is_not_required(spec.type):
            return UnpackerRegistry.get(spec.copy(type=get_args(spec.type)[0]))
        elif is_unpack(spec.type):
            unpacker = UnpackerRegistry.get(
                spec.copy(type=get_args(spec.type)[0])
            )
            return f"*{unpacker}"
        elif is_type_var_tuple(spec.type):
            return UnpackerRegistry.get(spec.copy(type=Tuple[Any, ...]))
        elif isinstance(spec.type, ForwardRef):
            evaluated = spec.builder.evaluate_forward_ref(
                spec.type, spec.owner
            )
            if evaluated is not None:
                return UnpackerRegistry.get(spec.copy(type=evaluated))
        elif is_type_alias_type(spec.type):
            return UnpackerRegistry.get(spec.copy(type=spec.type.__value__))
        raise UnserializableDataError(
            f"{spec.type} as a field type is not supported by mashumaro"
        )


@register
def unpack_number(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type in (int, float):
        return f"{type_name(spec.origin_type)}({spec.expression})"


@register
def unpack_bool_and_none(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type in (bool, NoneType, None):
        return spec.expression


@register
def unpack_date_objects(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type in (datetime.datetime, datetime.date, datetime.time):
        deserialize_option = get_overridden_deserialization_method(spec)
        if deserialize_option is not None:
            if deserialize_option == "ciso8601":
                if ciso8601:
                    spec.builder.ensure_module_imported(ciso8601)
                    datetime_parser = "ciso8601.parse_datetime"
                else:
                    raise ThirdPartyModuleNotFoundError(
                        "ciso8601", spec.field_ctx.name, spec.builder.cls
                    )  # pragma: no cover
            elif deserialize_option == "pendulum":
                if pendulum:
                    spec.builder.ensure_module_imported(pendulum)
                    datetime_parser = "pendulum.parse"
                else:
                    raise ThirdPartyModuleNotFoundError(
                        "pendulum", spec.field_ctx.name, spec.builder.cls
                    )  # pragma: no cover
            else:
                raise UnsupportedDeserializationEngine(
                    spec.field_ctx.name,
                    spec.type,
                    spec.builder.cls,
                    deserialize_option,
                )
            suffix = ""
            if spec.origin_type is datetime.date:
                suffix = ".date()"
            elif spec.origin_type is datetime.time:
                suffix = ".time()"
            return f"{datetime_parser}({spec.expression}){suffix}"
        method = f"__datetime_{spec.origin_type.__name__}_fromisoformat"
        spec.builder.ensure_object_imported(
            getattr(datetime, spec.origin_type.__name__).fromisoformat,
            method,
        )
        return f"{method}({spec.expression})"


@register
def unpack_timedelta(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is datetime.timedelta:
        method = "__datetime_timedelta"
        spec.builder.ensure_object_imported(datetime.timedelta, method)
        return f"{method}(seconds={spec.expression})"


@register
def unpack_timezone(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is datetime.timezone:
        spec.builder.ensure_object_imported(parse_timezone)
        return f"parse_timezone({spec.expression})"


@register
def unpack_zone_info(spec: ValueSpec) -> Optional[Expression]:
    if PY_39_MIN and spec.origin_type is zoneinfo.ZoneInfo:
        method = "__zoneinfo_ZoneInfo"
        spec.builder.ensure_object_imported(zoneinfo.ZoneInfo, method)
        return f"{method}({spec.expression})"


@register
def unpack_uuid(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is uuid.UUID:
        method = "__uuid_UUID"
        spec.builder.ensure_object_imported(uuid.UUID, method)
        return f"{method}({spec.expression})"


@register
def unpack_ipaddress(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type in (
        ipaddress.IPv4Address,
        ipaddress.IPv6Address,
        ipaddress.IPv4Network,
        ipaddress.IPv6Network,
        ipaddress.IPv4Interface,
        ipaddress.IPv6Interface,
    ):
        method = f"__ipaddress_{spec.origin_type.__name__}"
        spec.builder.ensure_object_imported(spec.origin_type, method)
        return f"{method}({spec.expression})"


@register
def unpack_decimal(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is Decimal:
        spec.builder.ensure_object_imported(Decimal)
        return f"Decimal({spec.expression})"


@register
def unpack_fraction(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is Fraction:
        spec.builder.ensure_object_imported(Fraction)
        return f"Fraction({spec.expression})"


def unpack_tuple(spec: ValueSpec, args: Tuple[Type, ...]) -> Expression:
    if not args:
        if spec.type in (Tuple, tuple):
            args = [typing.Any, ...]  # type: ignore
        else:
            return "()"
    elif len(args) == 1 and args[0] == ():
        if not PY_311_MIN:
            return "()"
    if len(args) == 2 and args[1] is Ellipsis:
        unpacker = UnpackerRegistry.get(
            spec.copy(type=args[0], expression="value", could_be_none=True)
        )
        return f"tuple([{unpacker} for value in {spec.expression}])"
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
        unpackers: List[Expression] = []
        for _idx, _arg_idx in enumerate(arg_indexes):
            if isinstance(_arg_idx, tuple):
                u_expr = f"{spec.expression}[{_arg_idx[0]}:{_arg_idx[1]}]"
            else:
                u_expr = f"{spec.expression}[{_arg_idx}]"
            unpacker = UnpackerRegistry.get(
                spec.copy(
                    type=args[_idx],
                    expression=u_expr,
                    could_be_none=True,
                )
            )
            if unpacker != "*()":  # workaround for empty tuples
                unpackers.append(unpacker)
        return f"tuple([{', '.join(unpackers)}])"


def unpack_named_tuple(spec: ValueSpec) -> Expression:
    resolved = resolve_type_params(spec.origin_type, get_args(spec.type))[
        spec.origin_type
    ]
    annotations = {
        k: resolved.get(v, v)
        for k, v in getattr(spec.origin_type, "__annotations__", {}).items()
    }
    fields = getattr(spec.type, "_fields", ())
    defaults = getattr(spec.type, "_field_defaults", {})
    unpackers = []
    as_dict = spec.builder.get_dialect_or_config_option(
        "namedtuple_as_dict", False
    )
    deserialize_option = get_overridden_deserialization_method(spec)
    if deserialize_option is not None:
        if deserialize_option == "as_dict":
            as_dict = True
        elif deserialize_option == "as_list":
            as_dict = False
        else:
            raise UnsupportedDeserializationEngine(
                field_name=spec.field_ctx.name,
                field_type=spec.type,
                holder_class=spec.builder.cls,
                engine=deserialize_option,
            )
    field_indices: Iterable[Any]
    if as_dict:
        field_indices = zip((f"'{name}'" for name in fields), fields)
    else:
        field_indices = enumerate(fields)
    if not defaults:
        packed_value = spec.expression
    else:
        packed_value = "value"
    for idx, field in field_indices:
        unpacker = UnpackerRegistry.get(
            spec.copy(
                type=annotations.get(field, Any),
                expression=f"{packed_value}[{idx}]",
                could_be_none=True,
            )
        )
        unpackers.append(unpacker)

    if not defaults:
        field_type = spec.builder.get_type_name_identifier(spec.type)
        return f"{field_type}({', '.join(unpackers)})"

    lines = CodeLines()
    method_name = (
        f"__unpack_named_tuple_{spec.builder.cls.__name__}_"
        f"{spec.field_ctx.name}__{random_hex()}"
    )
    default_kwargs = spec.builder.get_unpack_method_default_flag_values()
    if spec.builder.is_nailed:
        lines.append("@classmethod")
        method_args = "cls, value"
    else:
        method_args = "value"
    if default_kwargs:
        lines.append(f"def {method_name}({method_args}, {default_kwargs}):")
    else:  # pragma: no cover
        # we shouldn't be here because there will be default_kwargs
        lines.append(f"def {method_name}({method_args}):")
    with lines.indent():
        lines.append("fields = []")
        with lines.indent("try:"):
            for unpacker in unpackers:
                lines.append(f"fields.append({unpacker})")
        with lines.indent("except IndexError:"):
            lines.append("pass")
        field_type = spec.builder.get_type_name_identifier(spec.type)
        lines.append(f"return {field_type}(*fields)")
    lines.append(
        f"setattr({spec.cls_attrs_name}, '{method_name}', {method_name})"
    )
    if spec.builder.get_config().debug:
        print(f"{type_name(spec.builder.cls)}:")
        print(lines.as_text())
    exec(lines.as_text(), spec.builder.globals, spec.builder.__dict__)
    method_args = ", ".join(
        filter(None, (spec.expression, spec.builder.get_unpack_method_flags()))
    )
    return f"{spec.cls_attrs_name}.{method_name}({method_args})"


def unpack_typed_dict(spec: ValueSpec) -> Expression:
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
        f"__unpack_typed_dict_{spec.builder.cls.__name__}_"
        f"{spec.field_ctx.name}__{random_hex()}"
    )
    default_kwargs = spec.builder.get_unpack_method_default_flag_values()
    if spec.builder.is_nailed:
        lines.append("@classmethod")
        method_args = "cls, value"
    else:
        method_args = "value"
    if default_kwargs:
        lines.append(f"def {method_name}({method_args}, {default_kwargs}):")
    else:  # pragma: no cover
        # we shouldn't be here because there will be default_kwargs
        lines.append(f"def {method_name}({method_args}):")
    with lines.indent():
        lines.append("d = {}")
        for key in sorted(required_keys, key=all_keys.index):
            unpacker = UnpackerRegistry.get(
                spec.copy(
                    type=annotations[key],
                    expression=f"value['{key}']",
                    could_be_none=True,
                    owner=spec.type,
                )
            )
            lines.append(f"d['{key}'] = {unpacker}")
        for key in sorted(optional_keys, key=all_keys.index):
            lines.append(f"key_value = value.get('{key}', MISSING)")
            with lines.indent("if key_value is not MISSING:"):
                unpacker = UnpackerRegistry.get(
                    spec.copy(
                        type=annotations[key],
                        expression="key_value",
                        could_be_none=True,
                        owner=spec.type,
                    )
                )
                lines.append(f"d['{key}'] = {unpacker}")
        lines.append("return d")
    lines.append(
        f"setattr({spec.cls_attrs_name}, '{method_name}', {method_name})"
    )
    if spec.builder.get_config().debug:
        print(f"{type_name(spec.builder.cls)}:")
        print(lines.as_text())
    exec(lines.as_text(), spec.builder.globals, spec.builder.__dict__)
    method_args = ", ".join(
        filter(None, (spec.expression, spec.builder.get_unpack_method_flags()))
    )
    return f"{spec.cls_attrs_name}.{method_name}({method_args})"


@register
def unpack_collection(spec: ValueSpec) -> Optional[Expression]:
    if not issubclass(spec.origin_type, typing.Collection):
        return None
    elif issubclass(spec.origin_type, enum.Enum):
        return None

    args = get_args(spec.type)

    def inner_expr(
        arg_num: int = 0, v_name: str = "value", v_type: Optional[Type] = None
    ) -> Expression:
        if v_type:
            return UnpackerRegistry.get(
                spec.copy(type=v_type, expression=v_name)
            )
        else:
            if args and len(args) > arg_num:
                type_arg: Any = args[arg_num]
            else:
                type_arg = Any
            return UnpackerRegistry.get(
                spec.copy(
                    type=type_arg,
                    expression=v_name,
                    could_be_none=True,
                    field_ctx=spec.field_ctx.copy(metadata={}),
                )
            )

    if issubclass(spec.origin_type, typing.ByteString):  # type: ignore
        if spec.origin_type is bytes:
            spec.builder.ensure_object_imported(decodebytes)
            return f"decodebytes({spec.expression}.encode())"
        elif spec.origin_type is bytearray:
            spec.builder.ensure_object_imported(decodebytes)
            return f"bytearray(decodebytes({spec.expression}.encode()))"
    elif issubclass(spec.origin_type, str):
        return spec.expression
    elif ensure_generic_collection_subclass(spec, List):
        return f"[{inner_expr()} for value in {spec.expression}]"
    elif ensure_generic_collection_subclass(spec, typing.Deque):
        spec.builder.ensure_module_imported(collections)
        return (
            f"collections.deque([{inner_expr()} "
            f"for value in {spec.expression}])"
        )
    elif issubclass(spec.origin_type, Tuple):  # type: ignore
        if is_named_tuple(spec.origin_type):
            return unpack_named_tuple(spec)
        elif ensure_generic_collection(spec):
            return unpack_tuple(spec, args)
    elif ensure_generic_collection_subclass(spec, typing.FrozenSet):
        return f"frozenset([{inner_expr()} for value in {spec.expression}])"
    elif ensure_generic_collection_subclass(spec, typing.AbstractSet):
        return f"set([{inner_expr()} for value in {spec.expression}])"
    elif ensure_generic_mapping(spec, args, typing.ChainMap):
        spec.builder.ensure_module_imported(collections)
        return (
            f'collections.ChainMap(*[{{{inner_expr(0, "key")}:{inner_expr(1)} '
            f"for key, value in m.items()}} for m in {spec.expression}])"
        )
    elif ensure_generic_mapping(spec, args, typing.OrderedDict):
        spec.builder.ensure_module_imported(collections)
        return (
            f'collections.OrderedDict({{{inner_expr(0, "key")}: '
            f"{inner_expr(1)} for key, value in {spec.expression}.items()}})"
        )
    elif ensure_generic_mapping(spec, args, typing.DefaultDict):
        spec.builder.ensure_module_imported(collections)
        default_type = type_name(args[1] if args else None)
        return (
            f"collections.defaultdict({default_type}, "
            f"{{{inner_expr(0, 'key')}: "
            f"{inner_expr(1)} for key, value in {spec.expression}.items()}})"
        )
    elif ensure_generic_mapping(spec, args, typing.Counter):
        spec.builder.ensure_module_imported(collections)
        return (
            f'collections.Counter({{{inner_expr(0, "key")}: '
            f"{inner_expr(1, v_type=int)} "
            f"for key, value in {spec.expression}.items()}})"
        )
    elif is_typed_dict(spec.origin_type):
        return unpack_typed_dict(spec)
    elif issubclass(spec.origin_type, types.MappingProxyType):
        spec.builder.ensure_module_imported(types)
        return (
            f'types.MappingProxyType({{{inner_expr(0, "key")}: {inner_expr(1)}'
            f" for key, value in {spec.expression}.items()}})"
        )
    elif ensure_generic_mapping(spec, args, typing.Mapping):
        return (
            f'{{{inner_expr(0, "key")}: {inner_expr(1)} '
            f"for key, value in {spec.expression}.items()}}"
        )
    elif ensure_generic_collection_subclass(spec, typing.Sequence):
        return f"[{inner_expr()} for value in {spec.expression}]"


@register
def unpack_pathlike(spec: ValueSpec) -> Optional[Expression]:
    if spec.origin_type is os.PathLike:
        spec.builder.ensure_module_imported(pathlib)
        return f"{type_name(pathlib.PurePath)}({spec.expression})"
    elif issubclass(spec.origin_type, os.PathLike):
        field_type = spec.builder.get_type_name_identifier(spec.origin_type)
        return f"{field_type}({spec.expression})"


@register
def unpack_enum(spec: ValueSpec) -> Optional[Expression]:
    if issubclass(spec.origin_type, enum.Enum):
        field_type = spec.builder.get_type_name_identifier(spec.origin_type)
        return f"{field_type}({spec.expression})"
