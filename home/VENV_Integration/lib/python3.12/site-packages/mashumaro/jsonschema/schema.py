import datetime
import ipaddress
import os
import typing
import warnings
from base64 import encodebytes
from dataclasses import MISSING, dataclass, field, is_dataclass, replace
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from functools import cached_property
from typing import (
    Any,
    Callable,
    Dict,
    ForwardRef,
    Iterable,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
from uuid import UUID

from typing_extensions import TypeAlias

from mashumaro.config import BaseConfig
from mashumaro.core.const import PY_39_MIN, PY_311_MIN
from mashumaro.core.meta.code.builder import CodeBuilder
from mashumaro.core.meta.helpers import (
    evaluate_forward_ref,
    get_args,
    get_forward_ref_referencing_globals,
    get_function_return_annotation,
    get_literal_values,
    get_type_origin,
    is_annotated,
    is_generic,
    is_literal,
    is_named_tuple,
    is_new_type,
    is_not_required,
    is_required,
    is_special_typing_primitive,
    is_type_var,
    is_type_var_any,
    is_type_var_tuple,
    is_typed_dict,
    is_union,
    is_unpack,
    resolve_type_params,
    type_name,
)
from mashumaro.core.meta.types.common import NoneType
from mashumaro.helper import pass_through
from mashumaro.jsonschema.annotations import (
    Annotation,
    Contains,
    DependentRequired,
    ExclusiveMaximum,
    ExclusiveMinimum,
    MaxContains,
    Maximum,
    MaxItems,
    MaxLength,
    MaxProperties,
    MinContains,
    Minimum,
    MinItems,
    MinLength,
    MinProperties,
    MultipleOf,
    Pattern,
    UniqueItems,
)
from mashumaro.jsonschema.models import (
    DATETIME_FORMATS,
    IPADDRESS_FORMATS,
    Context,
    JSONArraySchema,
    JSONObjectSchema,
    JSONSchema,
    JSONSchemaInstanceFormatExtension,
    JSONSchemaInstanceType,
    JSONSchemaStringFormat,
)
from mashumaro.types import SerializationStrategy

if PY_39_MIN:
    from zoneinfo import ZoneInfo

try:
    from mashumaro.mixins.orjson import (
        DataClassORJSONMixin as DataClassJSONMixin,
    )
except ImportError:  # pragma: no cover
    from mashumaro.mixins.json import DataClassJSONMixin  # type: ignore


UTC_OFFSET_PATTERN = r"^UTC([+-][0-2][0-9]:[0-5][0-9])?$"


@dataclass
class Instance:
    type: Type
    name: Optional[str] = None

    __owner_builder: Optional[CodeBuilder] = None
    __self_builder: Optional[CodeBuilder] = None

    origin_type: Type = field(init=False)
    annotations: List[Annotation] = field(init=False, default_factory=list)

    @cached_property
    def metadata(self) -> Dict[str, Any]:
        if self.name and self.__owner_builder:
            return dict(**self.__owner_builder.metadatas.get(self.name, {}))
        else:
            return {}

    @property
    def _self_builder(self) -> CodeBuilder:
        assert self.__self_builder
        return self.__self_builder

    @property
    def alias(self) -> Optional[str]:
        alias = self.metadata.get("alias")
        if alias is None:
            aliases_config = self.get_owner_config().aliases
            alias = aliases_config.get(self.name)  # type: ignore
        if alias is None:
            alias = self.name
        return alias

    @property
    def owner_class(self) -> Optional[Type]:
        if self.__owner_builder:
            return self.__owner_builder.cls
        return None

    def derive(self, **changes: Any) -> "Instance":
        new_type = changes.get("type")
        if isinstance(new_type, ForwardRef):
            changes["type"] = evaluate_forward_ref(
                new_type,
                get_forward_ref_referencing_globals(new_type, self.type),
                self.__dict__,
            )
        new_instance = replace(self, **changes)
        if is_dataclass(self.origin_type):
            new_instance.__owner_builder = self.__self_builder
        return new_instance

    def __post_init__(self) -> None:
        self.update_type(self.type)
        if is_annotated(self.type):
            self.annotations = getattr(self.type, "__metadata__", [])
            self.type = get_args(self.type)[0]
            self.origin_type = get_type_origin(self.type)

    def update_type(self, new_type: Type) -> None:
        if self.__owner_builder:
            self.type = self.__owner_builder.get_real_type(
                field_name=self.name,  # type: ignore
                field_type=new_type,
            )
        self.origin_type = get_type_origin(self.type)
        if is_dataclass(self.origin_type):
            type_args = get_args(self.type)
            self.__self_builder = CodeBuilder(self.origin_type, type_args)
            self.__self_builder.reset()
        else:
            self.__self_builder = None

    def fields(self) -> Iterable[Tuple[str, Type, bool, Any]]:
        for f_name, f_type in self._self_builder.get_field_types(
            include_extras=True
        ).items():
            f = self._self_builder.dataclass_fields.get(f_name)
            if not f or f and not f.init:
                continue
            f_default = f.default
            if f_default is MISSING:
                f_default = self._self_builder.namespace.get(f_name, MISSING)
            if f_default is not MISSING:
                f_default = _default(f_type, f_default, self.get_self_config())

            has_default = (
                f.default is not MISSING or f.default_factory is not MISSING
            )

            yield f_name, f_type, has_default, f_default

    def get_overridden_serialization_method(
        self,
    ) -> Optional[Union[Callable, str]]:
        if not self.__owner_builder:
            return None
        serialize_option = self.metadata.get("serialize")
        if serialize_option is not None:
            if callable(serialize_option):
                self.metadata.pop("serialize", None)  # prevent recursion
            return serialize_option
        for strategy in self.__owner_builder.iter_serialization_strategies(
            self.metadata, self.type
        ):
            if strategy is pass_through:
                return pass_through
            elif isinstance(strategy, dict):
                serialize_option = strategy.get("serialize")
            elif isinstance(strategy, SerializationStrategy):
                serialize_option = strategy.serialize
            if serialize_option is not None:
                return serialize_option
        return None

    def get_owner_config(self) -> Type[BaseConfig]:
        if self.__owner_builder:
            return self.__owner_builder.get_config()
        else:
            return BaseConfig

    def get_owner_dialect_or_config_option(
        self, option: str, default: Any
    ) -> Any:
        if self.__owner_builder:
            return self.__owner_builder.get_dialect_or_config_option(
                option, default
            )
        else:
            return default

    def get_self_config(self) -> Type[BaseConfig]:
        if self.__self_builder:
            return self.__self_builder.get_config()
        else:
            return BaseConfig


InstanceSchemaCreator: TypeAlias = Callable[
    [Instance, Context], Optional[JSONSchema]
]


@dataclass
class InstanceSchemaCreatorRegistry:
    _registry: List[InstanceSchemaCreator] = field(default_factory=list)

    def register(self, func: InstanceSchemaCreator) -> InstanceSchemaCreator:
        self._registry.append(func)
        return func

    def iter(self) -> Iterable[InstanceSchemaCreator]:
        yield from self._registry


@dataclass
class EmptyJSONSchema(JSONSchema):
    pass


def get_schema(
    instance: Instance, ctx: Context, with_dialect_uri: bool = False
) -> JSONSchema:
    for schema_creator in Registry.iter():
        schema = schema_creator(instance, ctx)
        if schema is not None:
            if with_dialect_uri:
                schema.schema = ctx.dialect.uri
            return schema
    raise NotImplementedError(
        f'Type {type_name(instance.type)} of field "{instance.name}" '
        f"in {type_name(instance.owner_class)} isn't supported"
    )


def _get_schema_or_none(
    instance: Instance, ctx: Context
) -> Optional[JSONSchema]:
    schema = get_schema(instance, ctx)
    if isinstance(schema, EmptyJSONSchema):
        return None
    return schema


def _default(f_type: Type, f_value: Any, config_cls: Type[BaseConfig]) -> Any:
    @dataclass
    class CC(DataClassJSONMixin):
        x: f_type = f_value  # type: ignore

        class Config(config_cls):  # type: ignore
            pass

    return CC(f_value).to_dict()["x"]


Registry = InstanceSchemaCreatorRegistry()
register = Registry.register


BASIC_TYPES = {str, int, float, bool}


@register
def on_type_with_overridden_serialization(
    instance: Instance, ctx: Context
) -> Optional[JSONSchema]:
    def override_with_any(reason: Any) -> None:
        if instance.owner_class is not None:
            name = f"{type_name(instance.owner_class)}.{instance.name}"
        else:  # pragma: no cover
            # we will have an owner class, but leave this here just in case
            name = type_name(instance.type)
        warnings.warn(
            f"Type Any will be used for {name} with "
            f"overridden serialization method: {reason}"
        )
        instance.update_type(Any)  # type: ignore[arg-type]

    overridden_method = instance.get_overridden_serialization_method()
    if overridden_method is pass_through:
        return None
    elif overridden_method in BASIC_TYPES:
        instance.update_type(overridden_method)  # type: ignore
    elif callable(overridden_method):
        try:
            new_type = get_function_return_annotation(overridden_method)
            if new_type is instance.type:
                return None
            else:
                instance.update_type(new_type)
        except Exception as e:
            override_with_any(e)
        return get_schema(instance, ctx)


@register
def on_dataclass(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    # TODO: Self references might not work
    if is_dataclass(instance.origin_type):
        jsonschema_config = instance.get_self_config().json_schema
        schema = JSONObjectSchema(
            title=instance.origin_type.__name__,
            additionalProperties=jsonschema_config.get(
                "additionalProperties", False
            ),
        )
        properties: Dict[str, JSONSchema] = {}
        required = []
        field_schema_overrides = jsonschema_config.get("properties", {})
        for f_name, f_type, has_default, f_default in instance.fields():
            override = field_schema_overrides.get(f_name)
            f_instance = instance.derive(type=f_type, name=f_name)
            if override:
                f_schema = JSONSchema.from_dict(override)
            else:
                f_schema = get_schema(f_instance, ctx)
            if f_instance.alias:
                f_name = f_instance.alias
            if f_default is not MISSING:
                f_schema.default = f_default
            description = f_instance.metadata.get("description")
            if description:
                f_schema.description = description

            if not has_default:
                required.append(f_name)

            properties[f_name] = f_schema
        if properties:
            schema.properties = properties
        if required:
            schema.required = required
        if ctx.all_refs:
            ctx.definitions[instance.origin_type.__name__] = schema
            ref_prefix = ctx.ref_prefix or ctx.dialect.definitions_root_pointer
            return JSONSchema(
                reference=f"{ref_prefix}/{instance.origin_type.__name__}"
            )
        else:
            return schema


@register
def on_any(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.type is Any:
        return EmptyJSONSchema()


def on_literal(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    enum_values = []
    for value in get_literal_values(instance.type):
        if isinstance(value, Enum):
            enum_values.append(value.value)
        elif isinstance(value, (int, str, bool, NoneType)):  # type: ignore
            enum_values.append(value)
        elif isinstance(value, bytes):
            enum_values.append(encodebytes(value).decode())
    if len(enum_values) == 1:
        return JSONSchema(const=enum_values[0])
    else:
        return JSONSchema(enum=enum_values)


@register
def on_special_typing_primitive(
    instance: Instance, ctx: Context
) -> Optional[JSONSchema]:
    if not is_special_typing_primitive(instance.origin_type):
        return None

    args = get_args(instance.type)

    if is_union(instance.type):
        return JSONSchema(
            anyOf=[get_schema(instance.derive(type=arg), ctx) for arg in args]
        )
    elif is_type_var_any(instance.type):
        return EmptyJSONSchema()
    elif is_type_var(instance.type):
        constraints = getattr(instance.type, "__constraints__")
        if constraints:
            return JSONSchema(
                anyOf=[
                    get_schema(instance.derive(type=arg), ctx)
                    for arg in constraints
                ]
            )
        else:
            bound = getattr(instance.type, "__bound__")
            return get_schema(instance.derive(type=bound), ctx)
    elif is_new_type(instance.type):
        return get_schema(
            instance.derive(type=instance.type.__supertype__), ctx
        )
    elif is_literal(instance.type):
        return on_literal(instance, ctx)
    # elif is_self(instance.type):
    #     raise NotImplementedError
    elif is_required(instance.type) or is_not_required(instance.type):
        return get_schema(instance.derive(type=args[0]), ctx)
    elif is_unpack(instance.type):
        return get_schema(
            instance.derive(type=get_args(instance.type)[0]), ctx
        )
    elif is_type_var_tuple(instance.type):
        return get_schema(instance.derive(type=Tuple[Any, ...]), ctx)
    elif isinstance(instance.type, ForwardRef):
        evaluated = evaluate_forward_ref(
            instance.type,
            get_forward_ref_referencing_globals(instance.type),
            None,
        )
        if evaluated is not None:
            return get_schema(instance.derive(type=evaluated), ctx)


@register
def on_number(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.origin_type is int:
        schema = JSONSchema(type=JSONSchemaInstanceType.INTEGER)
    elif instance.origin_type is float:
        schema = JSONSchema(type=JSONSchemaInstanceType.NUMBER)
    else:
        return None
    for annotation in instance.annotations:
        if isinstance(annotation, Maximum):
            schema.maximum = annotation.value
        elif isinstance(annotation, Minimum):
            schema.minimum = annotation.value
        elif isinstance(annotation, ExclusiveMaximum):
            schema.exclusiveMaximum = annotation.value
        elif isinstance(annotation, ExclusiveMinimum):
            schema.exclusiveMinimum = annotation.value
        elif isinstance(annotation, MultipleOf):
            schema.multipleOf = annotation.value
    return schema


@register
def on_bool(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.origin_type is bool:
        return JSONSchema(type=JSONSchemaInstanceType.BOOLEAN)


@register
def on_none(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.origin_type in (NoneType, None):
        return JSONSchema(type=JSONSchemaInstanceType.NULL)


@register
def on_date_objects(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.origin_type in (
        datetime.datetime,
        datetime.date,
        datetime.time,
    ):
        return JSONSchema(
            type=JSONSchemaInstanceType.STRING,
            format=DATETIME_FORMATS[instance.origin_type],
        )


@register
def on_timedelta(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.origin_type is datetime.timedelta:
        return JSONSchema(
            type=JSONSchemaInstanceType.NUMBER,
            format=JSONSchemaInstanceFormatExtension.TIMEDELTA,
        )


@register
def on_timezone(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.origin_type is datetime.timezone:
        return JSONSchema(
            type=JSONSchemaInstanceType.STRING, pattern=UTC_OFFSET_PATTERN
        )


@register
def on_zone_info(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if PY_39_MIN and instance.origin_type is ZoneInfo:
        return JSONSchema(
            type=JSONSchemaInstanceType.STRING,
            format=JSONSchemaInstanceFormatExtension.TIME_ZONE,
        )


@register
def on_uuid(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.origin_type is UUID:
        return JSONSchema(
            type=JSONSchemaInstanceType.STRING,
            format=JSONSchemaStringFormat.UUID,
        )


@register
def on_ipaddress(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.origin_type in (
        ipaddress.IPv4Address,
        ipaddress.IPv6Address,
        ipaddress.IPv4Network,
        ipaddress.IPv6Network,
        ipaddress.IPv4Interface,
        ipaddress.IPv6Interface,
    ):
        return JSONSchema(
            type=JSONSchemaInstanceType.STRING,
            format=IPADDRESS_FORMATS[instance.origin_type],  # type: ignore
        )


@register
def on_decimal(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.origin_type is Decimal:
        return JSONSchema(
            type=JSONSchemaInstanceType.STRING,
            format=JSONSchemaInstanceFormatExtension.DECIMAL,
        )


@register
def on_fraction(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if instance.origin_type is Fraction:
        return JSONSchema(
            type=JSONSchemaInstanceType.STRING,
            format=JSONSchemaInstanceFormatExtension.FRACTION,
        )


def on_tuple(instance: Instance, ctx: Context) -> JSONArraySchema:
    args = get_args(instance.type)
    if not args:
        if instance.type in (Tuple, tuple):
            args = [typing.Any, ...]  # type: ignore
        else:
            return JSONArraySchema(maxItems=0)
    elif len(args) == 1 and args[0] == ():
        if not PY_311_MIN:
            return JSONArraySchema(maxItems=0)
    if len(args) == 2 and args[1] is Ellipsis:
        items_schema = _get_schema_or_none(instance.derive(type=args[0]), ctx)
        return JSONArraySchema(items=items_schema)
    else:
        min_items = 0
        max_items = 0
        prefix_items = []
        items: Optional[JSONSchema] = None
        unpack_schema: Optional[JSONSchema] = None
        unpack_idx = 0
        for arg_idx, arg in enumerate(args, start=1):
            if not is_unpack(arg):
                min_items += 1
                if not unpack_schema:
                    prefix_items.append(
                        get_schema(instance.derive(type=arg), ctx)
                    )
            else:
                unpack_schema = get_schema(instance.derive(type=arg), ctx)
                unpack_idx = arg_idx
        if unpack_schema:
            prefix_items.extend(unpack_schema.prefixItems or [])
            min_items += unpack_schema.minItems or 0
            max_items += unpack_schema.maxItems or 0
            if unpack_idx == len(args):
                items = unpack_schema.items
        else:
            min_items = len(args)
            max_items = len(args)
        return JSONArraySchema(
            prefixItems=prefix_items or None,
            items=items,
            minItems=min_items or None,
            maxItems=max_items or None,
        )


def on_named_tuple(instance: Instance, ctx: Context) -> JSONSchema:
    resolved = resolve_type_params(
        instance.origin_type, get_args(instance.type)
    )[instance.origin_type]
    annotations = {
        k: resolved.get(v, v)
        for k, v in getattr(
            instance.origin_type, "__annotations__", {}
        ).items()
    }
    fields = getattr(instance.type, "_fields", ())
    defaults = getattr(instance.type, "_field_defaults", {})
    as_dict = instance.get_owner_dialect_or_config_option(
        "namedtuple_as_dict", False
    )
    serialize_option = instance.get_overridden_serialization_method()
    if serialize_option == "as_dict":
        as_dict = True
    elif serialize_option == "as_list":
        as_dict = False
    properties = {}
    for f_name in fields:
        f_type = annotations.get(f_name, typing.Any)
        f_schema = get_schema(instance.derive(type=f_type), ctx)
        f_default = defaults.get(f_name, MISSING)
        if f_default is not MISSING:
            if isinstance(f_schema, EmptyJSONSchema):
                f_schema = JSONSchema()
            f_schema.default = _default(
                f_type, f_default, instance.get_self_config()
            )
        properties[f_name] = f_schema
    if as_dict:
        return JSONObjectSchema(
            properties=properties or None,
            required=list(fields),
            additionalProperties=False,
        )
    else:
        return JSONArraySchema(
            prefixItems=list(properties.values()) or None,
            maxItems=len(properties) or None,
            minItems=len(properties) or None,
        )


def on_typed_dict(instance: Instance, ctx: Context) -> JSONObjectSchema:
    resolved = resolve_type_params(
        instance.origin_type, get_args(instance.type)
    )[instance.origin_type]
    annotations = {
        k: resolved.get(v, v)
        for k, v in instance.origin_type.__annotations__.items()
    }
    all_keys = list(annotations.keys())
    required_keys = getattr(instance.type, "__required_keys__", all_keys)
    return JSONObjectSchema(
        properties={
            key: get_schema(instance.derive(type=annotations[key]), ctx)
            for key in all_keys
        }
        or None,
        required=sorted(required_keys) or None,
        additionalProperties=False,
    )


def apply_array_constraints(
    instance: Instance,
    schema: JSONSchema,
) -> JSONSchema:
    has_contains = False
    min_contains: Optional[int] = None
    max_contains: Optional[int] = None
    for annotation in instance.annotations:
        if isinstance(annotation, MinItems):
            schema.minItems = annotation.value
        elif isinstance(annotation, MaxItems):
            schema.maxItems = annotation.value
        elif isinstance(annotation, UniqueItems):
            schema.uniqueItems = annotation.value
        elif isinstance(annotation, Contains):
            schema.contains = annotation.value
            has_contains = True
        elif isinstance(annotation, MinContains):
            min_contains = annotation.value
        elif isinstance(annotation, MaxContains):
            max_contains = annotation.value
    if has_contains:
        if min_contains is not None:
            schema.minContains = min_contains
        if max_contains is not None:
            schema.maxContains = max_contains
    return schema


def apply_object_constraints(
    instance: Instance, schema: JSONSchema
) -> JSONSchema:
    for annotation in instance.annotations:
        if isinstance(annotation, MaxProperties):
            schema.maxProperties = annotation.value
        elif isinstance(annotation, MinProperties):
            schema.minProperties = annotation.value
        elif isinstance(annotation, DependentRequired):
            schema.dependentRequired = annotation.value
    return schema


@register
def on_collection(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if not issubclass(instance.origin_type, typing.Collection):
        return None
    elif issubclass(instance.origin_type, Enum):
        return None

    args = get_args(instance.type)

    if issubclass(instance.origin_type, typing.ByteString):  # type: ignore
        return JSONSchema(
            type=JSONSchemaInstanceType.STRING,
            format=JSONSchemaInstanceFormatExtension.BASE64,
        )
    elif issubclass(instance.origin_type, str):
        schema = JSONSchema(type=JSONSchemaInstanceType.STRING)
        for annotation in instance.annotations:
            if isinstance(annotation, MinLength):
                schema.minLength = annotation.value
            elif isinstance(annotation, MaxLength):
                schema.maxLength = annotation.value
            elif isinstance(annotation, Pattern):
                schema.pattern = annotation.value
        return schema
    elif is_generic(instance.type) and issubclass(
        instance.origin_type, (List, typing.Deque)
    ):
        return apply_array_constraints(
            instance,
            JSONArraySchema(
                items=(
                    _get_schema_or_none(instance.derive(type=args[0]), ctx)
                    if args
                    else None
                )
            ),
        )
    elif issubclass(instance.origin_type, Tuple):  # type: ignore
        if is_named_tuple(instance.origin_type):
            return apply_array_constraints(
                instance, on_named_tuple(instance, ctx)
            )
        elif is_generic(instance.type):
            return apply_array_constraints(instance, on_tuple(instance, ctx))
    elif is_generic(instance.type) and issubclass(
        instance.origin_type, (typing.FrozenSet, typing.AbstractSet)
    ):
        return apply_array_constraints(
            instance,
            JSONArraySchema(
                items=(
                    _get_schema_or_none(instance.derive(type=args[0]), ctx)
                    if args
                    else None
                ),
                uniqueItems=True,
            ),
        )
    elif is_generic(instance.type) and issubclass(
        instance.origin_type, typing.ChainMap
    ):
        return apply_array_constraints(
            instance,
            JSONArraySchema(
                items=get_schema(
                    instance=instance.derive(
                        type=(
                            Dict[args[0], args[1]]  # type: ignore
                            if args
                            else Dict
                        )
                    ),
                    ctx=ctx,
                )
            ),
        )
    elif is_generic(instance.type) and issubclass(
        instance.origin_type, typing.Counter
    ):
        schema = JSONObjectSchema(
            additionalProperties=get_schema(instance.derive(type=int), ctx),
        )
        if args:
            schema.propertyNames = _get_schema_or_none(
                instance.derive(type=args[0]), ctx
            )
        return apply_object_constraints(instance, schema)
    elif is_typed_dict(instance.origin_type):
        return on_typed_dict(instance, ctx)
    elif is_generic(instance.type) and issubclass(
        instance.origin_type, typing.Mapping
    ):
        schema = JSONObjectSchema(
            additionalProperties=(
                _get_schema_or_none(instance.derive(type=args[1]), ctx)
                if args
                else None
            ),
            propertyNames=(
                _get_schema_or_none(instance.derive(type=args[0]), ctx)
                if args
                else None
            ),
        )
        return apply_object_constraints(instance, schema)
    elif is_generic(instance.type) and issubclass(
        instance.origin_type, typing.Sequence
    ):
        return apply_array_constraints(
            instance,
            JSONArraySchema(
                items=(
                    _get_schema_or_none(instance.derive(type=args[0]), ctx)
                    if args
                    else None
                )
            ),
        )


@register
def on_pathlike(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if issubclass(instance.origin_type, os.PathLike):
        schema = JSONSchema(
            type=JSONSchemaInstanceType.STRING,
            format=JSONSchemaInstanceFormatExtension.PATH,
        )
        for annotation in instance.annotations:
            if isinstance(annotation, MaxLength):
                schema.maxLength = annotation.value
            elif isinstance(annotation, MinLength):
                schema.minLength = annotation.value
        return schema


@register
def on_enum(instance: Instance, ctx: Context) -> Optional[JSONSchema]:
    if issubclass(instance.origin_type, Enum):
        return JSONSchema(enum=[m.value for m in instance.origin_type])


__all__ = ["Instance", "get_schema"]
