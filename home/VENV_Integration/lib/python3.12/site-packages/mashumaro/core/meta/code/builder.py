import enum
import importlib
import inspect
import math
import types
import typing
import uuid
from contextlib import contextmanager

# noinspection PyProtectedMember
from dataclasses import _FIELDS  # type: ignore
from dataclasses import MISSING, Field, is_dataclass
from functools import lru_cache

try:
    from dataclasses import KW_ONLY  # type: ignore
except ImportError:
    KW_ONLY = object()  # type: ignore

import typing_extensions

from mashumaro.config import (
    ADD_DIALECT_SUPPORT,
    ADD_SERIALIZATION_CONTEXT,
    TO_DICT_ADD_BY_ALIAS_FLAG,
    TO_DICT_ADD_OMIT_NONE_FLAG,
    BaseConfig,
    SerializationStrategyValueType,
)
from mashumaro.core.const import Sentinel
from mashumaro.core.helpers import ConfigValue
from mashumaro.core.meta.code.lines import CodeLines
from mashumaro.core.meta.helpers import (
    evaluate_forward_ref,
    get_args,
    get_class_that_defines_field,
    get_class_that_defines_method,
    get_forward_ref_referencing_globals,
    get_literal_values,
    get_name_error_name,
    get_type_annotations,
    hash_type_args,
    is_annotated,
    is_class_var,
    is_dataclass_dict_mixin,
    is_dataclass_dict_mixin_subclass,
    is_dialect_subclass,
    is_hashable,
    is_init_var,
    is_literal,
    is_local_type_name,
    is_named_tuple,
    is_optional,
    is_type_var_any,
    resolve_type_params,
    substitute_type_params,
    type_name,
)
from mashumaro.core.meta.types.common import (
    FieldContext,
    NoneType,
    ValueSpec,
    clean_id,
)
from mashumaro.core.meta.types.pack import PackerRegistry
from mashumaro.core.meta.types.unpack import (
    SubtypeUnpackerBuilder,
    UnpackerRegistry,
)
from mashumaro.dialect import Dialect
from mashumaro.exceptions import (  # noqa
    BadDialect,
    BadHookSignature,
    ExtraKeysError,
    InvalidFieldValue,
    MissingDiscriminatorError,
    MissingField,
    SuitableVariantNotFoundError,
    ThirdPartyModuleNotFoundError,
    UnresolvedTypeReferenceError,
    UnserializableDataError,
    UnserializableField,
    UnsupportedDeserializationEngine,
    UnsupportedSerializationEngine,
)
from mashumaro.types import Alias, Discriminator

__PRE_SERIALIZE__ = "__pre_serialize__"
__PRE_DESERIALIZE__ = "__pre_deserialize__"
__POST_SERIALIZE__ = "__post_serialize__"
__POST_DESERIALIZE__ = "__post_deserialize__"


SIMPLE_TYPES = (int, float, bool, str, NoneType)


class InternalMethodName(str):
    _PREFIX = "__mashumaro_"
    _SUFFIX = "__"

    @classmethod
    def from_public(cls, value: str) -> "InternalMethodName":
        return cls(f"{cls._PREFIX}{value}{cls._SUFFIX}")

    @property
    def public(self) -> str:
        return self[len(self._PREFIX) : -len(self._SUFFIX)]


class CodeBuilder:
    def __init__(
        self,
        cls: typing.Type,
        type_args: typing.Tuple[typing.Type, ...] = (),
        dialect: typing.Optional[typing.Type[Dialect]] = None,
        first_method: str = "from_dict",
        allow_postponed_evaluation: bool = True,
        format_name: str = "dict",
        decoder: typing.Optional[typing.Any] = None,
        encoder: typing.Optional[typing.Any] = None,
        encoder_kwargs: typing.Optional[typing.Dict[str, typing.Any]] = None,
        default_dialect: typing.Optional[typing.Type[Dialect]] = None,
        attrs: typing.Any = None,
        attrs_registry: typing.Optional[
            typing.Dict[typing.Any, typing.Any]
        ] = None,
    ):
        self.cls = cls
        self.lines: CodeLines = CodeLines()
        self.globals: typing.Dict[str, typing.Any] = {}
        self.resolved_type_params: typing.Dict[
            typing.Type, typing.Dict[typing.Type, typing.Type]
        ] = {}
        self.field_classes: typing.Dict = {}
        self.initial_type_args = type_args
        if dialect is not None and not is_dialect_subclass(dialect):
            raise BadDialect(
                'Keyword argument "dialect" must be a subclass of Dialect '
                f"in {type_name(self.cls)}.{first_method}"
            )
        self.dialect = dialect
        self.default_dialect = default_dialect
        self.allow_postponed_evaluation = allow_postponed_evaluation
        self.format_name = format_name
        self.decoder = decoder
        self.encoder = encoder
        self.encoder_kwargs = encoder_kwargs or {}

        if attrs is not None:
            self.attrs = attrs
        else:
            self.attrs = cls
        if attrs_registry is not None:
            self.attrs_registry = attrs_registry
        else:
            self.attrs_registry = {}

    def reset(self) -> None:
        self.lines.reset()
        self.globals = globals().copy()
        self.resolved_type_params = resolve_type_params(
            self.cls, self.initial_type_args
        )
        self.field_classes = {}

    @property
    def namespace(self) -> typing.Mapping[typing.Any, typing.Any]:
        return self.cls.__dict__

    @property
    def annotations(self) -> typing.Dict[str, typing.Any]:
        return self.namespace.get("__annotations__", {})

    @property
    def is_nailed(self) -> bool:
        return self.attrs is self.cls

    def __get_field_types(
        self, recursive: bool = True, include_extras: bool = False
    ) -> typing.Dict[str, typing.Any]:
        fields = {}
        try:
            field_type_hints = typing_extensions.get_type_hints(
                self.cls, include_extras=include_extras
            )
        except NameError as e:
            name = get_name_error_name(e)
            raise UnresolvedTypeReferenceError(self.cls, name) from None
        for fname, ftype in field_type_hints.items():
            if is_class_var(ftype) or is_init_var(ftype) or ftype is KW_ONLY:
                continue
            if recursive or fname in self.annotations:
                fields[fname] = ftype
        return fields

    def _get_field_class(self, field_name: str) -> typing.Any:
        try:
            cls = self.field_classes[field_name]
        except KeyError:
            cls = get_class_that_defines_field(field_name, self.cls)
            self.field_classes[field_name] = cls
        return cls

    def get_real_type(
        self, field_name: str, field_type: typing.Type
    ) -> typing.Type:
        cls = self._get_field_class(field_name)
        return substitute_type_params(
            field_type, self.resolved_type_params[cls]
        )

    def get_field_resolved_type_params(
        self, field_name: str
    ) -> typing.Dict[typing.Type, typing.Type]:
        cls = self._get_field_class(field_name)
        return self.resolved_type_params[cls]

    def get_field_types(
        self, include_extras: bool = False
    ) -> typing.Dict[str, typing.Any]:
        return self.__get_field_types(include_extras=include_extras)

    def get_type_name_identifier(
        self,
        typ: typing.Optional[typing.Type],
        resolved_type_params: typing.Optional[
            typing.Dict[typing.Type, typing.Type]
        ] = None,
    ) -> str:
        field_type = type_name(typ, resolved_type_params=resolved_type_params)

        if is_local_type_name(field_type):
            field_type = clean_id(field_type)
            self.ensure_object_imported(typ, field_type)

        return field_type

    @property
    @lru_cache()
    def dataclass_fields(self) -> typing.Dict[str, Field]:
        d = {}
        for ancestor in self.cls.__mro__[-1:0:-1]:
            if is_dataclass(ancestor):
                for field in getattr(ancestor, _FIELDS).values():
                    d[field.name] = field
        for name in self.__get_field_types(recursive=False):
            field = self.namespace.get(name, MISSING)
            if isinstance(field, Field):
                d[name] = field
            else:
                field = self.namespace.get(_FIELDS, {}).get(name, MISSING)
                if isinstance(field, Field):
                    d[name] = field
                else:
                    d.pop(name, None)
        return d

    @property
    def metadatas(self) -> typing.Dict[str, typing.Mapping[str, typing.Any]]:
        return {
            name: field.metadata
            for name, field in self.dataclass_fields.items()
        }

    @lru_cache(None)
    def get_field_default(
        self, name: str, call_factory: bool = False
    ) -> typing.Any:
        field = self.dataclass_fields.get(name)
        if field:
            if field.default is not MISSING:
                return field.default
            else:
                if call_factory and field.default_factory is not MISSING:
                    return field.default_factory()
                else:
                    return field.default_factory
        else:
            return self.namespace.get(name, MISSING)

    def add_type_modules(self, *types_: typing.Type) -> None:
        for t in types_:
            module = inspect.getmodule(t)
            if not module:
                continue
            self.ensure_module_imported(module)
            if is_literal(t):
                literal_args = get_literal_values(t)
                self.add_type_modules(*literal_args)
            else:
                args = get_args(t)
                if args:
                    self.add_type_modules(*args)
            constraints = getattr(t, "__constraints__", ())
            if constraints:
                self.add_type_modules(*constraints)
            bound = getattr(t, "__bound__", ())
            if bound:
                self.add_type_modules(bound)

    def ensure_module_imported(self, module: types.ModuleType) -> None:
        self.globals.setdefault(module.__name__, module)
        package = module.__name__.split(".")[0]
        self.globals.setdefault(package, importlib.import_module(package))

    def ensure_object_imported(
        self,
        obj: typing.Any,
        name: typing.Optional[str] = None,
    ) -> None:
        self.globals.setdefault(name or obj.__name__, obj)

    def add_line(self, line: str) -> None:
        self.lines.append(line)

    @contextmanager
    def indent(
        self,
        expr: typing.Optional[str] = None,
    ) -> typing.Generator[None, None, None]:
        with self.lines.indent(expr):
            yield

    def compile(self) -> None:
        code = self.lines.as_text()
        if self.get_config().debug:
            if self.dialect is not None:
                print(f"{type_name(self.cls)}[{type_name(self.dialect)}]:")
            else:
                print(f"{type_name(self.cls)}:")
            print(code)
        exec(code, self.globals, self.__dict__)

    def evaluate_forward_ref(
        self,
        typ: typing.ForwardRef,
        owner: typing.Optional[typing.Type],
    ) -> typing.Optional[typing.Type]:
        globalns = get_forward_ref_referencing_globals(
            typ, owner, self.globals
        )
        return evaluate_forward_ref(typ, globalns, self.__dict__)

    def get_declared_hook(self, method_name: str) -> typing.Any:
        cls = get_class_that_defines_method(method_name, self.cls)
        if cls is not None and not is_dataclass_dict_mixin(cls):
            return cls.__dict__[method_name]

    def _add_unpack_method_lines_lazy(self, method_name: str) -> None:
        if self.default_dialect is not None:
            self.add_type_modules(self.default_dialect)
        self.add_line(
            f"CodeBuilder("
            f"cls,"
            f"first_method='{method_name}',"
            f"allow_postponed_evaluation=False,"
            f"format_name='{self.format_name}',"
            f"decoder={type_name(self.decoder)},"
            f"default_dialect={type_name(self.default_dialect)}"
            f").add_unpack_method()"
        )
        unpacker_args = [
            "d",
            self.get_unpack_method_flags(pass_decoder=True),
        ]
        unpacker_args_s = ", ".join(filter(None, unpacker_args))
        self.add_line(f"return cls.{method_name}({unpacker_args_s})")

    def _add_unpack_method_lines(self, method_name: str) -> None:
        config = self.get_config()
        if (
            config.lazy_compilation
            and self.allow_postponed_evaluation
            and self.is_nailed
        ):
            self._add_unpack_method_lines_lazy(method_name)
            return
        try:
            field_types = self.get_field_types(include_extras=True)
        except UnresolvedTypeReferenceError:
            if (
                not self.allow_postponed_evaluation
                or not config.allow_postponed_evaluation
            ):
                raise
            self._add_unpack_method_lines_lazy(method_name)
        else:
            if self.decoder is not None:
                self.add_line("d = decoder(d)")
            discr = self.get_discriminator()
            if discr:
                if not discr.include_subtypes:
                    raise ValueError(
                        "Config based discriminator must have "
                        "'include_subtypes' enabled"
                    )
                discr = Discriminator(
                    # prevent RecursionError
                    field=discr.field,
                    include_subtypes=discr.include_subtypes,
                    variant_tagger_fn=discr.variant_tagger_fn,
                )
                self.add_type_modules(self.cls)
                method = SubtypeUnpackerBuilder(discr).build(
                    spec=ValueSpec(
                        type=self.cls,
                        expression="d",
                        builder=self,
                        field_ctx=FieldContext("", {}),
                    )
                )
                self.add_line(f"return {method}")
                return
            pre_deserialize = self.get_declared_hook(__PRE_DESERIALIZE__)
            if pre_deserialize:
                if not isinstance(pre_deserialize, classmethod):
                    raise BadHookSignature(
                        f"`{__PRE_DESERIALIZE__}` must be a class method with "
                        "Callable[[Dict[Any, Any]], Dict[Any, Any]] signature"
                    )
                else:
                    self.add_line(f"d = cls.{__PRE_DESERIALIZE__}(d)")
            post_deserialize = self.get_declared_hook(__POST_DESERIALIZE__)
            if post_deserialize:
                if not isinstance(post_deserialize, classmethod):
                    raise BadHookSignature(
                        f"`{__POST_DESERIALIZE__}` must be a class method "
                        f"with Callable[[{type_name(self.cls)}], "
                        f"{type_name(self.cls)}] signature"
                    )
            filtered_fields = []
            pos_args = []
            kw_args = []
            missing_kw_only = False
            add_kwargs = False
            kw_only_fields = set()
            field_blocks = []
            for fname, ftype in field_types.items():
                field = self.dataclass_fields.get(fname)
                if field and not field.init:
                    continue
                if missing_kw_only:
                    kw_only_fields.add(fname)
                elif field:
                    kw_only = getattr(field, "kw_only", MISSING)
                    if kw_only is MISSING:
                        missing_kw_only = True
                        kw_only_fields.add(fname)
                    elif kw_only:
                        kw_only_fields.add(fname)
                else:
                    missing_kw_only = True
                    kw_only_fields.add(fname)

                metadata = self.metadatas.get(fname, {})
                alias = self.__get_field_alias(fname, ftype, metadata, config)

                filtered_fields.append((fname, alias, ftype))
            if filtered_fields:
                if config.forbid_extra_keys:
                    allowed_keys = {f[1] or f[0] for f in filtered_fields}

                    # If a discriminator with a field is set via config,
                    # we should allow this field to be present in the input
                    # This will not work for annotated discriminators though...
                    discr = self.get_discriminator(look_in_parents=True)
                    if discr and discr.field:
                        allowed_keys.add(discr.field)

                    if config.allow_deserialization_not_by_alias:
                        allowed_keys |= {f[0] for f in filtered_fields}

                    allowed_keys_str = "'" + "', '".join(allowed_keys) + "'"

                    self.add_line("d_keys = set(d.keys())")
                    self.add_line(
                        f"forbidden_keys = d_keys - {{{allowed_keys_str}}}"
                    )
                    with self.indent("if forbidden_keys:"):
                        self.add_line(
                            "raise ExtraKeysError(forbidden_keys,cls) "
                            "from None"
                        )

                with self.indent("try:"):
                    for fname, alias, ftype in filtered_fields:
                        self.add_type_modules(ftype)
                        metadata = self.metadatas.get(fname, {})
                        field_block = FieldUnpackerCodeBlockBuilder(
                            self, self.lines.branch_off()
                        ).build(
                            fname=fname,
                            ftype=ftype,
                            metadata=metadata,
                            alias=alias,
                        )
                        if field_block.in_kwargs:
                            add_kwargs = True
                        field_blocks.append(field_block)
                    if add_kwargs:
                        self.add_line("kwargs = {}")
                    in_kwargs = False
                    for field_block in field_blocks:
                        self.lines.extend(field_block.lines)
                        if field_block.in_kwargs:
                            in_kwargs = True
                        else:
                            if (
                                field_block.fname in kw_only_fields
                                or in_kwargs
                            ):
                                kw_args.append(field_block.fname)
                            else:
                                pos_args.append(field_block.fname)
                with self.indent("except AttributeError:"):
                    with self.indent("if not isinstance(d, dict):"):
                        self.add_line(
                            "raise ValueError('Argument for "
                            f"{type_name(self.cls)}.{method_name} method "
                            "should be a dict instance') from None"
                        )
                    with self.indent("else:"):
                        self.add_line("raise")

            args = [f"__{f}" for f in pos_args]
            for kw_arg in kw_args:
                args.append(f"{kw_arg}=__{kw_arg}")
            if add_kwargs:
                args.append("**kwargs")
            cls_inst = f"cls({', '.join(args)})"

            if post_deserialize:
                self.add_line(f"return cls.{__POST_DESERIALIZE__}({cls_inst})")
            else:
                self.add_line(f"return {cls_inst}")

    def _add_unpack_method_with_dialect_lines(self, method_name: str) -> None:
        if self.decoder is not None:
            self.add_line("d = decoder(d)")
        unpacker_args = ", ".join(
            filter(None, ("cls", "d", self.get_unpack_method_flags()))
        )
        cache_name = f"__dialect_{self.format_name}_unpacker_cache__"
        self.add_line(f"unpacker = cls.{cache_name}.get(dialect)")
        with self.indent("if unpacker is not None:"):
            self.add_line(f"return unpacker({unpacker_args})")
        if self.default_dialect:
            self.add_type_modules(self.default_dialect)
        self.add_line(
            "CodeBuilder("
            "cls,dialect=dialect,"
            f"first_method='{method_name}',"
            f"format_name='{self.format_name}',"
            f"default_dialect={type_name(self.default_dialect)}"
            ").add_unpack_method()"
        )
        self.add_line(f"return cls.{cache_name}[dialect]({unpacker_args})")

    def add_unpack_method(self) -> None:
        self.reset()
        method_name = self.get_unpack_method_name(
            type_args=self.initial_type_args,
            format_name=self.format_name,
            decoder=self.decoder,
        )
        if self.decoder is not None:
            self.add_type_modules(self.decoder)
        dialects_feature = self.is_code_generation_option_enabled(
            ADD_DIALECT_SUPPORT
        )
        cache_name = f"__dialect_{self.format_name}_unpacker_cache__"
        if dialects_feature:
            with self.indent(f"if not '{cache_name}' in cls.__dict__:"):
                self.add_line(f"cls.{cache_name} = {{}}")

        if self.dialect is None and self.is_nailed:
            self.add_line("@classmethod")
        self._add_unpack_method_definition(method_name)
        with self.indent():
            if dialects_feature and self.dialect is None:
                with self.indent("if dialect is None:"):
                    self._add_unpack_method_lines(method_name)
                with self.indent("else:"):
                    self._add_unpack_method_with_dialect_lines(method_name)
            else:
                self._add_unpack_method_lines(method_name)
        self._add_setattr_method(method_name, cache_name)
        self.compile()

    def _add_unpack_method_definition(self, method_name: str) -> None:
        kwargs = ""
        default_kwargs = self.get_unpack_method_default_flag_values(
            pass_decoder=True
        )
        if default_kwargs:
            kwargs += f", {default_kwargs}"

        if self.is_nailed:
            self.add_line(f"def {method_name}(cls, d{kwargs}):")
        else:
            self.add_line(f"def {method_name}(d{kwargs}):")

    @lru_cache()
    @typing.no_type_check
    def get_config(
        self,
        cls: typing.Optional[typing.Type] = None,
        look_in_parents: bool = True,
    ) -> typing.Type[BaseConfig]:
        if cls is None:
            cls = self.cls
        if look_in_parents:
            config_cls = getattr(cls, "Config", BaseConfig)
        else:
            config_cls = cls.__dict__.get("Config", BaseConfig)
        if not issubclass(config_cls, BaseConfig):
            config_cls = type(
                "Config",
                (BaseConfig, config_cls),
                {**BaseConfig.__dict__, **config_cls.__dict__},
            )
        return config_cls

    def get_discriminator(
        self, look_in_parents: bool = False
    ) -> typing.Optional[Discriminator]:
        if look_in_parents:
            classes = self.cls.__mro__
        else:
            classes = (self.cls,)
        for cls in classes:
            discriminator = self.get_config(
                cls, look_in_parents=False
            ).discriminator
            if discriminator:
                return discriminator
        return None

    def get_pack_method_flags(
        self,
        cls: typing.Optional[typing.Type] = None,
        pass_encoder: bool = False,
    ) -> str:
        pluggable_flags = []
        if pass_encoder and self.encoder is not None:
            pluggable_flags.append("encoder=encoder")
            for value in self._get_encoder_kwargs(cls).values():
                pluggable_flags.append(f"{value[0]}={value[0]}")

        for option, flag in (
            (TO_DICT_ADD_OMIT_NONE_FLAG, "omit_none"),
            (TO_DICT_ADD_BY_ALIAS_FLAG, "by_alias"),
            (ADD_DIALECT_SUPPORT, "dialect"),
            (ADD_SERIALIZATION_CONTEXT, "context"),
        ):
            if self.is_code_generation_option_enabled(option, cls):
                if self.is_code_generation_option_enabled(option):
                    pluggable_flags.append(f"{flag}={flag}")
        return ", ".join(pluggable_flags)

    def get_unpack_method_flags(
        self,
        cls: typing.Optional[typing.Type] = None,
        pass_decoder: bool = False,
    ) -> str:
        pluggable_flags = []
        if pass_decoder and self.decoder is not None:
            pluggable_flags.append("decoder=decoder")
        for option, flag in ((ADD_DIALECT_SUPPORT, "dialect"),):
            if self.is_code_generation_option_enabled(option, cls):
                if self.is_code_generation_option_enabled(option):
                    pluggable_flags.append(f"{flag}={flag}")
        return ", ".join(pluggable_flags)

    def get_pack_method_default_flag_values(
        self,
        cls: typing.Optional[typing.Type] = None,
        pass_encoder: bool = False,
    ) -> str:
        pos_param_names = []
        pos_param_values = []
        kw_param_names = []
        kw_param_values = []
        if pass_encoder and self.encoder is not None:
            pos_param_names.append("encoder")
            pos_param_values.append(type_name(self.encoder))
            for value in self._get_encoder_kwargs(cls).values():
                kw_param_names.append(value[0])
                kw_param_values.append(value[1])

        omit_none_feature = self.is_code_generation_option_enabled(
            TO_DICT_ADD_OMIT_NONE_FLAG, cls
        )
        if omit_none_feature:
            omit_none = self.get_dialect_or_config_option("omit_none", False)
            kw_param_names.append("omit_none")
            kw_param_values.append("True" if omit_none else "False")

        by_alias_feature = self.is_code_generation_option_enabled(
            TO_DICT_ADD_BY_ALIAS_FLAG, cls
        )
        if by_alias_feature:
            serialize_by_alias = self.get_dialect_or_config_option(
                "serialize_by_alias", False, cls
            )
            kw_param_names.append("by_alias")
            kw_param_values.append("True" if serialize_by_alias else "False")

        dialects_feature = self.is_code_generation_option_enabled(
            ADD_DIALECT_SUPPORT, cls
        )
        if dialects_feature:
            kw_param_names.append("dialect")
            kw_param_values.append("None")

        context_feature = self.is_code_generation_option_enabled(
            ADD_SERIALIZATION_CONTEXT, cls
        )
        if context_feature:
            kw_param_names.append("context")
            kw_param_values.append("None")

        if pos_param_names:
            pluggable_flags_str = ", ".join(
                [f"{n}={v}" for n, v in zip(pos_param_names, pos_param_values)]
            )
        else:
            pluggable_flags_str = ""
        if kw_param_names:
            if pos_param_names:
                pluggable_flags_str += ", "
            pluggable_flags_str += "*, " + ", ".join(
                [f"{n}={v}" for n, v in zip(kw_param_names, kw_param_values)]
            )
        return pluggable_flags_str

    def get_unpack_method_default_flag_values(
        self, pass_decoder: bool = False
    ) -> str:
        pos_param_names = []
        pos_param_values = []
        kw_param_names = []
        kw_param_values = []

        if pass_decoder and self.decoder is not None:
            pos_param_names.append("decoder")
            pos_param_values.append(type_name(self.decoder))

        kw_param_names.append("dialect")
        kw_param_values.append("None")

        if pos_param_names:
            pluggable_flags_str = ", ".join(
                [f"{n}={v}" for n, v in zip(pos_param_names, pos_param_values)]
            )
        else:
            pluggable_flags_str = ""

        if kw_param_names:
            if pos_param_names:
                pluggable_flags_str += ", "
            pluggable_flags_str += "*, " + ", ".join(
                [f"{n}={v}" for n, v in zip(kw_param_names, kw_param_values)]
            )

        return pluggable_flags_str

    def is_code_generation_option_enabled(
        self, option: str, cls: typing.Optional[typing.Type] = None
    ) -> bool:
        if cls is None:
            cls = self.cls
        return option in self.get_config(cls).code_generation_options

    @classmethod
    def get_unpack_method_name(
        cls,
        type_args: typing.Iterable = (),
        format_name: str = "dict",
        decoder: typing.Optional[typing.Any] = None,
    ) -> InternalMethodName:
        if format_name != "dict" and decoder is not None:
            return InternalMethodName.from_public(f"from_{format_name}")
        else:
            method_name = "from_dict"
            if format_name != "dict":
                method_name += f"_{format_name}"
            if type_args:
                method_name += f"_{hash_type_args(type_args)}"
            return InternalMethodName.from_public(method_name)

    @classmethod
    def get_pack_method_name(
        cls,
        type_args: typing.Tuple[typing.Type, ...] = (),
        format_name: str = "dict",
        encoder: typing.Optional[typing.Any] = None,
    ) -> InternalMethodName:
        if format_name != "dict" and encoder is not None:
            return InternalMethodName.from_public(f"to_{format_name}")
        else:
            method_name = "to_dict"
            if format_name != "dict":
                method_name += f"_{format_name}"
            if type_args:
                method_name += f"_{hash_type_args(type_args)}"
            return InternalMethodName.from_public(f"{method_name}")

    def _add_pack_method_lines_lazy(self, method_name: str) -> None:
        if self.default_dialect is not None:
            self.add_type_modules(self.default_dialect)
        self.add_line(
            "CodeBuilder("
            "self.__class__,"
            f"first_method='{method_name}',"
            "allow_postponed_evaluation=False,"
            f"format_name='{self.format_name}',"
            f"encoder={type_name(self.encoder)},"
            f"encoder_kwargs={self._get_encoder_kwargs()},"
            f"default_dialect={type_name(self.default_dialect)}"
            ").add_pack_method()"
        )
        packer_args = self.get_pack_method_flags(pass_encoder=True)
        self.add_line(f"return self.{method_name}({packer_args})")

    def _add_pack_method_lines(self, method_name: str) -> None:
        config = self.get_config()
        if (
            config.lazy_compilation
            and self.allow_postponed_evaluation
            and self.is_nailed
        ):
            self._add_pack_method_lines_lazy(method_name)
            return
        try:
            field_types = self.get_field_types(include_extras=True)
        except UnresolvedTypeReferenceError:
            if (
                not self.allow_postponed_evaluation
                or not config.allow_postponed_evaluation
            ):
                raise
            self._add_pack_method_lines_lazy(method_name)
        else:
            pre_serialize = self.get_declared_hook(__PRE_SERIALIZE__)
            if pre_serialize:
                if self.is_code_generation_option_enabled(
                    ADD_SERIALIZATION_CONTEXT
                ):
                    pre_serialize_args = "context=context"
                else:
                    pre_serialize_args = ""
                self.add_line(
                    f"self = self.{__PRE_SERIALIZE__}({pre_serialize_args})"
                )
            by_alias_feature = self.is_code_generation_option_enabled(
                TO_DICT_ADD_BY_ALIAS_FLAG
            )
            omit_none_feature = self.is_code_generation_option_enabled(
                TO_DICT_ADD_OMIT_NONE_FLAG
            )
            serialize_by_alias = self.get_dialect_or_config_option(
                "serialize_by_alias", False
            )
            omit_none = self.get_dialect_or_config_option("omit_none", False)
            omit_default = self.get_dialect_or_config_option(
                "omit_default", False
            )
            force_value = omit_default
            packers = {}
            aliases = {}
            nullable_fields = set()
            nontrivial_nullable_fields = set()
            fnames_and_types: typing.Iterable[
                typing.Tuple[str, typing.Any]
            ] = field_types.items()
            if self.get_config().sort_keys:
                fnames_and_types = sorted(fnames_and_types, key=lambda x: x[0])

            for fname, ftype in fnames_and_types:
                if self.metadatas.get(fname, {}).get("serialize") == "omit":
                    continue
                packer, alias, could_be_none = self._get_field_packer(
                    fname, ftype, config, force_value
                )
                packers[fname] = packer
                if alias:
                    aliases[fname] = alias
                if could_be_none:
                    nullable_fields.add(fname)
                    if packer != "value":
                        nontrivial_nullable_fields.add(fname)
            if (
                nontrivial_nullable_fields
                or nullable_fields
                and (omit_none or omit_none_feature)
                or by_alias_feature
                and aliases
                or omit_default
            ):
                kwargs = "kwargs"
                self.add_line("kwargs = {}")
                for fname, packer in packers.items():
                    if force_value:
                        self.add_line(f"value = self.{fname}")
                    alias = aliases.get(fname)
                    if omit_default:
                        # do not call default_factory if we don't need to
                        default = self.get_field_default(
                            fname, call_factory=True
                        )
                    else:
                        default = None
                    if fname in nullable_fields:
                        if (
                            packer == "value"
                            and not omit_none
                            and not omit_none_feature
                            and not (omit_default and default is None)
                        ):
                            self._pack_method_set_value(
                                fname=fname,
                                alias=alias,
                                by_alias_feature=by_alias_feature,
                                packed_value=(
                                    "value" if force_value else f"self.{fname}"
                                ),
                                omit_default=omit_default,
                            )
                            continue
                        if not force_value:  # to add it only once
                            self.add_line(f"value = self.{fname}")
                        with self.indent("if value is not None:"):
                            self._pack_method_set_value(
                                fname=fname,
                                alias=alias,
                                by_alias_feature=by_alias_feature,
                                packed_value=packer,
                                omit_default=(
                                    omit_default and default is not None
                                ),
                            )
                        if omit_none and not omit_none_feature:
                            continue
                        elif omit_default and default is None:
                            continue
                        with self.indent("else:"):
                            if omit_none_feature:
                                with self.indent("if not omit_none:"):
                                    self._pack_method_set_value(
                                        fname=fname,
                                        alias=alias,
                                        by_alias_feature=by_alias_feature,
                                        packed_value="None",
                                        omit_default=False,
                                    )
                            else:
                                self._pack_method_set_value(
                                    fname=fname,
                                    alias=alias,
                                    by_alias_feature=by_alias_feature,
                                    packed_value="None",
                                    omit_default=False,
                                )
                    else:
                        self._pack_method_set_value(
                            fname=fname,
                            alias=alias,
                            by_alias_feature=by_alias_feature,
                            packed_value=packer,
                            omit_default=omit_default,
                        )
            else:
                kwargs_parts = []
                for fname, packer in packers.items():
                    if serialize_by_alias:
                        fname_or_alias = aliases.get(fname, fname)
                    else:
                        fname_or_alias = fname
                    kwargs_parts.append(
                        (
                            fname_or_alias,
                            packer if packer != "value" else f"self.{fname}",
                        )
                    )
                kwargs = ", ".join(f"'{k}': {v}" for k, v in kwargs_parts)
                kwargs = f"{{{kwargs}}}"
            post_serialize = self.get_declared_hook(__POST_SERIALIZE__)
            if self.encoder is not None:
                if self.encoder_kwargs:
                    encoder_options = ", ".join(
                        f"{k}={v[0]}" for k, v in self.encoder_kwargs.items()
                    )
                    return_statement = (
                        f"return encoder({{}}, {encoder_options})"
                    )
                else:
                    return_statement = "return encoder({})"
            else:
                return_statement = "return {}"
            if post_serialize:
                if self.is_code_generation_option_enabled(
                    ADD_SERIALIZATION_CONTEXT
                ):
                    kwargs = f"{kwargs}, context=context"
                self.add_line(
                    return_statement.format(
                        f"self.{__POST_SERIALIZE__}({kwargs})"
                    )
                )
            else:
                self.add_line(return_statement.format(kwargs))

    def _pack_method_set_value(
        self,
        fname: str,
        alias: typing.Optional[str],
        by_alias_feature: bool,
        packed_value: str,
        omit_default: bool,
    ) -> None:
        if omit_default:
            default = self.get_field_default(fname, call_factory=True)
            if default is not MISSING:
                default_literal = self.get_field_default_literal(
                    self.get_field_default(fname, call_factory=True)
                )
                # if default is None:
                #     comp_expr = f"value is not {default_literal}"
                if isinstance(default, float) and math.isnan(default):
                    self.ensure_object_imported(math.isnan, "isnan")
                    comp_expr = "not isnan(value)"
                else:
                    comp_expr = f"value != {default_literal}"
                with self.indent(f"if {comp_expr}:"):
                    return self.__pack_method_set_value(
                        fname, alias, by_alias_feature, packed_value
                    )
        return self.__pack_method_set_value(
            fname, alias, by_alias_feature, packed_value
        )

    def __pack_method_set_value(
        self,
        fname: str,
        alias: typing.Optional[str],
        by_alias_feature: bool,
        packed_value: str,
    ) -> None:
        if by_alias_feature and alias is not None:
            with self.indent("if by_alias:"):
                self.add_line(f"kwargs['{alias}'] = {packed_value}")
            with self.indent("else:"):
                self.add_line(f"kwargs['{fname}'] = {packed_value}")
        else:
            serialize_by_alias = self.get_dialect_or_config_option(
                "serialize_by_alias", False
            )
            if serialize_by_alias and alias is not None:
                fname_or_alias = alias
            else:
                fname_or_alias = fname
            self.add_line(f"kwargs['{fname_or_alias}'] = {packed_value}")

    def _add_pack_method_with_dialect_lines(self, method_name: str) -> None:
        packer_args = ", ".join(
            filter(None, ("self", self.get_pack_method_flags()))
        )
        cache_name = f"__dialect_{self.format_name}_packer_cache__"
        self.add_line(f"packer = self.__class__.{cache_name}.get(dialect)")
        self.add_line("if packer is not None:")
        if self.encoder is not None:
            return_statement = "return encoder({})"
        else:
            return_statement = "return {}"
        with self.indent():
            self.add_line(return_statement.format(f"packer({packer_args})"))
        if self.default_dialect:
            self.add_type_modules(self.default_dialect)
        self.add_line(
            "CodeBuilder("
            "self.__class__,dialect=dialect,"
            f"first_method='{method_name}',"
            f"format_name='{self.format_name}',"
            f"default_dialect={type_name(self.default_dialect)}"
            ").add_pack_method()"
        )
        self.add_line(
            return_statement.format(
                f"self.__class__.{cache_name}[dialect]({packer_args})"
            )
        )

    def _get_encoder_kwargs(
        self, cls: typing.Optional[typing.Type] = None
    ) -> typing.Dict[str, typing.Any]:
        result = {}
        for encoder_param, value in self.encoder_kwargs.items():
            packer_param = value[0]
            packer_value = value[1]
            if isinstance(packer_value, ConfigValue):
                packer_value = getattr(self.get_config(cls), packer_value.name)
            result[encoder_param] = (packer_param, packer_value)
        return result

    def _add_pack_method_definition(self, method_name: str) -> None:
        kwargs = ""
        default_kwargs = self.get_pack_method_default_flag_values(
            pass_encoder=True
        )
        if default_kwargs:
            kwargs += f", {default_kwargs}"
        self.add_line(f"def {method_name}(self{kwargs}):")

    def add_pack_method(self) -> None:
        self.reset()
        method_name = self.get_pack_method_name(
            type_args=self.initial_type_args,
            format_name=self.format_name,
            encoder=self.encoder,
        )
        if self.encoder is not None:
            self.add_type_modules(self.encoder)
        dialects_feature = self.is_code_generation_option_enabled(
            ADD_DIALECT_SUPPORT
        )
        cache_name = f"__dialect_{self.format_name}_packer_cache__"
        if dialects_feature:
            with self.indent(f"if not '{cache_name}' in cls.__dict__:"):
                self.add_line(f"cls.{cache_name} = {{}}")

        self._add_pack_method_definition(method_name)
        with self.indent():
            if dialects_feature and self.dialect is None:
                with self.indent("if dialect is None:"):
                    self._add_pack_method_lines(method_name)
                with self.indent("else:"):
                    self._add_pack_method_with_dialect_lines(method_name)
            else:
                self._add_pack_method_lines(method_name)
        self._add_setattr_method(method_name, cache_name)
        self.compile()

    def _add_setattr_method(
        self, method_name: InternalMethodName, cache_name: str
    ) -> None:
        if self.dialect is None:
            if not self.is_nailed:
                self.ensure_object_imported(self.attrs, "_cls")
                self.ensure_object_imported(self.cls, "cls")
                self.add_line(f"setattr(_cls, '{method_name}', {method_name})")
            else:
                self.add_line(f"setattr(cls, '{method_name}', {method_name})")
                if is_dataclass_dict_mixin_subclass(self.cls):
                    self.add_line(
                        f"setattr(cls, '{method_name.public}', {method_name})"
                    )
        else:
            self.add_line(f"cls.{cache_name}[dialect] = {method_name}")

    def _get_field_packer(
        self,
        fname: str,
        ftype: typing.Type,
        config: typing.Type[BaseConfig],
        force_value: bool = False,
    ) -> typing.Tuple[str, typing.Optional[str], bool]:
        metadata = self.metadatas.get(fname, {})
        alias = self.__get_field_alias(fname, ftype, metadata, config)
        could_be_none = (
            ftype in (typing.Any, type(None), None)
            or is_type_var_any(self.get_real_type(fname, ftype))
            or is_optional(ftype, self.get_field_resolved_type_params(fname))
            or self.get_field_default(fname) is None
        )
        value = "value" if could_be_none or force_value else f"self.{fname}"
        packer = PackerRegistry.get(
            ValueSpec(
                type=ftype,
                expression=value,
                builder=self,
                field_ctx=FieldContext(
                    name=fname,
                    metadata=metadata,
                ),
                could_be_none=False,
                no_copy_collections=self.get_dialect_or_config_option(
                    "no_copy_collections", ()
                ),
            )
        )
        return packer, alias, could_be_none

    @staticmethod
    def __get_field_alias(
        fname: str,
        ftype: typing.Type,
        metadata: typing.Mapping[str, typing.Any],
        config: typing.Type[BaseConfig],
    ) -> typing.Optional[str]:
        alias = metadata.get("alias")
        if alias is None and is_annotated(ftype):
            annotations = get_type_annotations(ftype)
            for ann in annotations:
                if isinstance(ann, Alias):
                    alias = ann.name
        if alias is None:
            alias = config.aliases.get(fname)
        return alias

    @typing.no_type_check
    def iter_serialization_strategies(
        self, metadata: typing.Mapping, ftype: typing.Type
    ) -> typing.Iterator[SerializationStrategyValueType]:
        if is_hashable(ftype):
            yield metadata.get("serialization_strategy")
            yield from self.__iter_serialization_strategies(ftype)

    @typing.no_type_check
    def __iter_serialization_strategies(
        self, ftype: typing.Type
    ) -> typing.Iterator[SerializationStrategyValueType]:
        if self.dialect is not None:
            yield self.dialect.serialization_strategy.get(ftype)
        default_dialect = self.get_config().dialect
        if default_dialect is not None:
            if not is_dialect_subclass(default_dialect):
                raise BadDialect(
                    'Config option "dialect" of '
                    f"{type_name(self.cls)} must be a subclass of Dialect"
                )
            yield default_dialect.serialization_strategy.get(ftype)
        yield self.get_config().serialization_strategy.get(ftype)
        if self.default_dialect is not None:
            yield self.default_dialect.serialization_strategy.get(ftype)

    def get_dialect_or_config_option(
        self,
        option: str,
        default: typing.Any,
        cls: typing.Optional[typing.Type] = None,
    ) -> typing.Any:
        for ns in (
            self.dialect,
            self.get_config(cls).dialect,
            self.get_config(cls),
            self.default_dialect,
        ):
            value = getattr(ns, option, Sentinel.MISSING)
            if value is not Sentinel.MISSING:
                return value
        return default

    def get_field_default_literal(self, value: typing.Any) -> str:
        if isinstance(value, enum.IntFlag):
            return str(value.value)
        elif type(value) in (str, int, bool, NoneType):  # type: ignore
            return repr(value)
        elif (
            isinstance(value, float)
            and not math.isnan(value)
            and not math.isinf(value)
        ):
            return repr(value)
        elif isinstance(value, tuple) and not is_named_tuple(type(value)):
            return repr(value)
        else:
            name = f"v_{uuid.uuid4().hex}"
            self.ensure_object_imported(value, name)
            return name


class FieldUnpackerCodeBlock:
    def __init__(self, lines: CodeLines, fname: str, in_kwargs: bool):
        self.lines = lines
        self.fname = fname
        self.in_kwargs = in_kwargs


class FieldUnpackerCodeBlockBuilder:
    def __init__(self, parent: CodeBuilder, lines: CodeLines):
        self.parent = parent
        self.lines = lines

    def _try_set_value(
        self,
        field_name: str,
        field_type_name: str,
        unpacked_value: str,
        in_kwargs: bool,
    ) -> None:
        with self.lines.indent("try:"):
            self._set_value(field_name, unpacked_value, in_kwargs)
        with self.lines.indent("except:"):
            self.lines.append(
                "raise InvalidFieldValue("
                f"'{field_name}',{field_type_name},value,cls)"
            )

    def _set_value(
        self, fname: str, unpacked_value: str, in_kwargs: bool = False
    ) -> None:
        if in_kwargs:
            self.lines.append(f"kwargs['{fname}'] = {unpacked_value}")
        else:
            self.lines.append(f"__{fname} = {unpacked_value}")

    def build(
        self,
        fname: str,
        ftype: typing.Type,
        metadata: typing.Mapping,
        *,
        alias: typing.Optional[str] = None,
    ) -> FieldUnpackerCodeBlock:
        default = self.parent.get_field_default(fname)
        has_default = default is not MISSING
        field_type = self.parent.get_type_name_identifier(
            ftype,
            resolved_type_params=self.parent.get_field_resolved_type_params(
                fname
            ),
        )
        could_be_none = (
            ftype in (typing.Any, type(None), None)
            or is_type_var_any(self.parent.get_real_type(fname, ftype))
            or is_optional(
                ftype, self.parent.get_field_resolved_type_params(fname)
            )
            or default is None
        )
        unpacked_value = UnpackerRegistry.get(
            ValueSpec(
                type=ftype,
                expression="value",
                builder=self.parent,
                field_ctx=FieldContext(
                    name=fname,
                    metadata=metadata,
                ),
                could_be_none=False if could_be_none else True,
            )
        )
        if self.parent.get_config().allow_deserialization_not_by_alias:
            if unpacked_value != "value":
                self.add_line(f"value = d.get('{alias}', MISSING)")
                with self.indent("if value is MISSING:"):
                    self.add_line(f"value = d.get('{fname}', MISSING)")
                packed_value = "value"
            elif has_default:
                self.add_line(f"value = d.get('{alias}', MISSING)")
                with self.indent("if value is MISSING:"):
                    self.add_line(f"value = d.get('{fname}', MISSING)")
                packed_value = "value"
            else:
                self.add_line(f"__{fname} = d.get('{alias}', MISSING)")
                with self.indent(f"if __{fname} is MISSING:"):
                    self.add_line(f"__{fname} = d.get('{fname}', MISSING)")
                packed_value = f"__{fname}"
                unpacked_value = packed_value
        else:
            if unpacked_value != "value":
                self.add_line(f"value = d.get('{alias or fname}', MISSING)")
                packed_value = "value"
            elif has_default:
                self.add_line(f"value = d.get('{alias or fname}', MISSING)")
                packed_value = "value"
            else:
                self.add_line(
                    f"__{fname} = d.get('{alias or fname}', MISSING)"
                )
                packed_value = f"__{fname}"
                unpacked_value = packed_value
        if not has_default:
            with self.indent(f"if {packed_value} is MISSING:"):
                self.add_line(
                    f"raise MissingField('{fname}',{field_type},cls) from None"
                )
            if packed_value != unpacked_value:
                if could_be_none:
                    with self.indent(f"if {packed_value} is not None:"):
                        self._try_set_value(
                            fname, field_type, unpacked_value, has_default
                        )
                    with self.indent("else:"):
                        self._set_value(fname, "None", has_default)
                else:
                    self._try_set_value(
                        fname, field_type, unpacked_value, has_default
                    )
        else:
            with self.indent(f"if {packed_value} is not MISSING:"):
                if could_be_none:
                    if unpacked_value != "value":
                        with self.indent(f"if {packed_value} is not None:"):
                            self._try_set_value(
                                fname, field_type, unpacked_value, has_default
                            )
                        if default is not None:
                            with self.indent("else:"):
                                self._set_value(fname, "None", has_default)
                    else:
                        self._set_value(fname, unpacked_value, has_default)
                else:
                    if unpacked_value != "value":
                        self._try_set_value(
                            fname, field_type, unpacked_value, has_default
                        )
                    else:
                        self._set_value(fname, unpacked_value, has_default)
        return FieldUnpackerCodeBlock(self.lines, fname, has_default)

    def add_line(self, line: str) -> None:
        self.lines.append(line)

    @contextmanager
    def indent(
        self,
        expr: typing.Optional[str] = None,
    ) -> typing.Generator[None, None, None]:
        with self.lines.indent(expr):
            yield
