import dataclasses
import enum
import inspect
import re
import sys
import types
import typing
from contextlib import suppress

# noinspection PyProtectedMember
from dataclasses import _FIELDS  # type: ignore
from hashlib import md5
from typing import (
    Any,
    ClassVar,
    Dict,
    ForwardRef,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

try:
    from typing import Unpack  # type: ignore[attr-defined]
except ImportError:
    from typing_extensions import Unpack

import typing_extensions

from mashumaro.core.const import (
    PEP_585_COMPATIBLE,
    PY_38,
    PY_39,
    PY_39_MIN,
    PY_310_MIN,
    PY_311_MIN,
    PY_312_MIN,
)
from mashumaro.dialect import Dialect

__all__ = [
    "get_type_origin",
    "get_args",
    "type_name",
    "is_special_typing_primitive",
    "is_generic",
    "is_typed_dict",
    "is_named_tuple",
    "is_optional",
    "is_union",
    "not_none_type_arg",
    "is_type_var",
    "is_type_var_any",
    "is_class_var",
    "is_final",
    "is_init_var",
    "get_class_that_defines_method",
    "get_class_that_defines_field",
    "is_dataclass_dict_mixin",
    "is_dataclass_dict_mixin_subclass",
    "collect_type_params",
    "resolve_type_params",
    "substitute_type_params",
    "get_generic_name",
    "get_name_error_name",
    "is_dialect_subclass",
    "is_new_type",
    "is_annotated",
    "get_type_annotations",
    "is_literal",
    "is_local_type_name",
    "get_literal_values",
    "is_self",
    "is_required",
    "is_not_required",
    "get_function_arg_annotation",
    "get_function_return_annotation",
    "is_unpack",
    "is_type_var_tuple",
    "hash_type_args",
    "iter_all_subclasses",
    "is_hashable",
    "is_hashable_type",
    "evaluate_forward_ref",
    "get_forward_ref_referencing_globals",
    "is_type_alias_type",
]


NoneType = type(None)
DataClassDictMixinPath = (
    f"{__name__.rsplit('.', 3)[:-3][0]}.mixins.dict.DataClassDictMixin"
)


def get_type_origin(typ: Type) -> Type:
    try:
        return typ.__origin__
    except AttributeError:
        return typ


def is_builtin_type(typ: Type) -> bool:
    try:
        return typ.__module__ == "builtins"
    except AttributeError:
        return False


def get_generic_name(typ: Type, short: bool = False) -> str:
    name = getattr(typ, "_name", None)
    if name is None:
        origin = get_type_origin(typ)
        if origin is typ:
            return type_name(origin, short, is_type_origin=True)
        else:
            return get_generic_name(origin, short)
    if short:
        return name
    else:
        return f"{typ.__module__}.{name}"


def get_args(typ: Optional[Type]) -> Tuple[Type, ...]:
    return getattr(typ, "__args__", ())


def _get_args_str(
    typ: Type,
    short: bool,
    resolved_type_params: Optional[Dict[Type, Type]] = None,
    limit: Optional[int] = None,
    none_type_as_none: bool = False,
    sep: str = ", ",
) -> str:
    if typ == Tuple[()]:
        return "()"
    elif PEP_585_COMPATIBLE and typ == tuple[()]:  # type: ignore
        return "()"
    args = _flatten_type_args(get_args(typ)[:limit])
    to_join = []
    for arg in args:
        to_join.append(
            type_name(
                typ=arg,
                short=short,
                resolved_type_params=resolved_type_params,
                none_type_as_none=none_type_as_none,
            )
        )
    if len(to_join) > 1:
        return sep.join(s for s in to_join if s != "()")
    else:
        return sep.join(to_join)


def get_literal_values(typ: Type) -> Tuple[Any, ...]:
    values = typ.__args__
    result: List[Any] = []
    for value in values:
        if is_literal(value):
            result.extend(get_literal_values(value))
        else:
            result.append(value)
    return tuple(result)


def _get_literal_values_str(typ: Type, short: bool) -> str:
    values_str = []
    for value in get_literal_values(typ):
        if isinstance(value, enum.Enum):
            values_str.append(f"{type_name(type(value), short)}.{value.name}")
        elif isinstance(
            value,
            (int, str, bytes, bool, NoneType),  # type: ignore
        ):
            values_str.append(repr(value))
    return ", ".join(values_str)


def _typing_name(
    typ_name: str,
    short: bool = False,
    module_name: str = "typing",
) -> str:
    return typ_name if short else f"{module_name}.{typ_name}"


def type_name(
    typ: Optional[Type],
    short: bool = False,
    resolved_type_params: Optional[Dict[Type, Type]] = None,
    is_type_origin: bool = False,
    none_type_as_none: bool = False,
) -> str:
    if resolved_type_params is None:
        resolved_type_params = {}
    if typ is None:
        return "None"
    elif typ is NoneType and none_type_as_none:
        return "None"
    elif typ is Ellipsis:
        return "..."
    elif typ is Any:
        return _typing_name("Any", short)
    elif is_optional(typ, resolved_type_params):
        args_str = type_name(
            typ=not_none_type_arg(get_args(typ), resolved_type_params),
            short=short,
            resolved_type_params=resolved_type_params,
        )
        return f"{_typing_name('Optional', short)}[{args_str}]"
    elif is_union(typ):
        args_str = _get_args_str(
            typ, short, resolved_type_params, none_type_as_none=True
        )
        return f"{_typing_name('Union', short)}[{args_str}]"
    elif is_annotated(typ):
        return type_name(get_args(typ)[0], short, resolved_type_params)
    elif not is_type_origin and is_literal(typ):
        args_str = _get_literal_values_str(typ, short)
        return f"{_typing_name('Literal', short, typ.__module__)}[{args_str}]"
    elif not is_type_origin and is_unpack(typ):
        if (
            typ in resolved_type_params
            and resolved_type_params[typ] is not typ
        ):
            return type_name(
                resolved_type_params[typ], short, resolved_type_params
            )
        else:
            unpacked_type_arg = get_args(typ)[0]
            if not is_variable_length_tuple(
                unpacked_type_arg
            ) and not is_type_var_tuple(unpacked_type_arg):
                return _get_args_str(
                    unpacked_type_arg, short, resolved_type_params
                )
            unpacked_type_name = type_name(
                unpacked_type_arg, short, resolved_type_params
            )
            if PY_311_MIN:
                return f"*{unpacked_type_name}"
            else:
                _unpack = _typing_name("Unpack", short, typ.__module__)
                return f"{_unpack}[{unpacked_type_name}]"
    elif not is_type_origin and is_generic(typ):
        args_str = _get_args_str(typ, short, resolved_type_params)
        if not args_str:
            return get_generic_name(typ, short)
        else:
            return f"{get_generic_name(typ, short)}[{args_str}]"
    elif is_builtin_type(typ):
        return typ.__qualname__
    elif is_type_var(typ):
        if (
            typ in resolved_type_params
            and resolved_type_params[typ] is not typ
        ):
            return type_name(
                resolved_type_params[typ], short, resolved_type_params
            )
        elif is_type_var_any(typ):
            return _typing_name("Any", short)
        constraints = getattr(typ, "__constraints__")
        if constraints:
            args_str = ", ".join(
                type_name(c, short, resolved_type_params) for c in constraints
            )
            return f"{_typing_name('Union', short)}[{args_str}]"
        else:
            if type_var_has_default(typ):
                bound = get_type_var_default(typ)
            else:
                bound = getattr(typ, "__bound__")
            return type_name(bound, short, resolved_type_params)
    elif is_new_type(typ) and not PY_310_MIN:
        # because __qualname__ and __module__ are messed up
        typ = typ.__supertype__
    try:
        if short:
            return typ.__qualname__  # type: ignore
        else:
            return f"{typ.__module__}.{typ.__qualname__}"  # type: ignore
    except AttributeError:
        return str(typ)


def is_special_typing_primitive(typ: Any) -> bool:
    try:
        issubclass(typ, object)
        return False
    except TypeError:
        return True


def is_generic(typ: Type) -> bool:
    with suppress(Exception):
        if hasattr(typ, "__class_getitem__"):
            return True
    if PY_38:
        # noinspection PyProtectedMember
        # noinspection PyUnresolvedReferences
        return issubclass(typ.__class__, typing._GenericAlias)  # type: ignore
    elif PY_39_MIN:
        # noinspection PyProtectedMember
        # noinspection PyUnresolvedReferences
        if (
            issubclass(typ.__class__, typing._BaseGenericAlias)  # type: ignore
            or type(typ) is types.GenericAlias  # type: ignore  # noqa: E721
        ):
            return True
        else:
            return False
        # else:  # for PEP 585 generics without args
        #     try:
        #         return (
        #             hasattr(typ, "__class_getitem__")
        #             and type(typ[str]) is types.GenericAlias  # type: ignore
        #         )
        #     except (TypeError, AttributeError):
        #         return False
    else:
        raise NotImplementedError


def is_typed_dict(typ: Type) -> bool:
    for module in (typing, typing_extensions):
        with suppress(AttributeError):
            if type(typ) is getattr(module, "_TypedDictMeta"):
                return True
    return False


def is_named_tuple(typ: Type) -> bool:
    try:
        return issubclass(typ, typing.Tuple) and hasattr(  # type: ignore
            typ, "_fields"
        )
    except TypeError:
        return False


def is_new_type(typ: Type) -> bool:
    return hasattr(typ, "__supertype__")


def is_union(typ: Type) -> bool:
    try:
        if PY_310_MIN and isinstance(typ, types.UnionType):  # type: ignore
            return True
        return typ.__origin__ is Union
    except AttributeError:
        return False


def is_optional(
    typ: Type, resolved_type_params: Optional[Dict[Type, Type]] = None
) -> bool:
    if resolved_type_params is None:
        resolved_type_params = {}
    if not is_union(typ):
        return False
    args = get_args(typ)
    if len(args) != 2:
        return False
    for arg in args:
        if resolved_type_params.get(arg, arg) is NoneType:
            return True
    return False


def is_annotated(typ: Type) -> bool:
    for module in (typing, typing_extensions):
        with suppress(AttributeError):
            if type(typ) is getattr(module, "_AnnotatedAlias"):
                return True
    return False


def get_type_annotations(typ: Type) -> Sequence[Any]:
    return getattr(typ, "__metadata__", [])


def is_literal(typ: Type) -> bool:
    if PY_38 or PY_39:
        with suppress(AttributeError):
            return is_generic(typ) and get_generic_name(typ, True) == "Literal"
    elif PY_310_MIN:
        with suppress(AttributeError):
            # noinspection PyProtectedMember
            # noinspection PyUnresolvedReferences
            return type(typ) is typing._LiteralGenericAlias  # type: ignore
    return False


def is_local_type_name(typ_name: str) -> bool:
    return "<locals>" in typ_name


def not_none_type_arg(
    type_args: Tuple[Type, ...],
    resolved_type_params: Optional[Dict[Type, Type]] = None,
) -> Optional[Type]:
    if resolved_type_params is None:
        resolved_type_params = {}
    for type_arg in type_args:
        if resolved_type_params.get(type_arg, type_arg) is not NoneType:
            return type_arg
    return None


def is_type_var(typ: Type) -> bool:
    return hasattr(typ, "__constraints__")


def is_type_var_any(typ: Type) -> bool:
    if not is_type_var(typ):
        return False
    elif typ.__constraints__ != ():
        return False
    elif typ.__bound__ not in (None, Any):
        return False
    elif type_var_has_default(typ):
        return False
    else:
        return True


def is_class_var(typ: Type) -> bool:
    return get_type_origin(typ) is ClassVar


def is_final(typ: Type) -> bool:
    return get_type_origin(typ) is typing_extensions.Final


def is_init_var(typ: Type) -> bool:
    return isinstance(typ, dataclasses.InitVar)


def get_class_that_defines_method(
    method_name: str, cls: Type
) -> Optional[Type]:
    for cls in cls.__mro__:
        if method_name in cls.__dict__:
            return cls
    return None


def get_class_that_defines_field(field_name: str, cls: Type) -> Optional[Type]:
    prev_cls = None
    prev_field = None
    for base in reversed(cls.__mro__):
        if dataclasses.is_dataclass(base):
            field = getattr(base, _FIELDS).get(field_name)
            if field and field != prev_field:
                prev_field = field
                prev_cls = base
    return prev_cls or cls


def is_dataclass_dict_mixin(typ: Type) -> bool:
    return type_name(typ) == DataClassDictMixinPath


def is_dataclass_dict_mixin_subclass(typ: Type) -> bool:
    with suppress(AttributeError):
        for cls in typ.__mro__:
            if is_dataclass_dict_mixin(cls):
                return True
    return False


def get_orig_bases(typ: Type) -> Tuple[Type, ...]:
    return getattr(typ, "__orig_bases__", ())


def collect_type_params(typ: Type) -> Sequence[Type]:
    type_params = []
    for type_arg in get_args(typ):
        if type_arg in type_params:
            continue
        elif is_type_var(type_arg):
            type_params.append(type_arg)
        elif is_unpack(type_arg) and is_type_var_tuple(get_args(type_arg)[0]):
            type_params.append(type_arg)
        else:
            for _type_param in collect_type_params(type_arg):
                if _type_param not in type_params:
                    type_params.append(_type_param)
    return type_params


def _check_generic(
    typ: Type, type_params: Sequence[Type], type_args: Sequence[Type]
) -> None:
    # https://github.com/python/cpython/issues/99382
    unpacks = len(list(filter(is_unpack, type_params)))
    if unpacks > 1:
        raise TypeError(
            "Multiple unpacks are disallowed within a single type parameter "
            f"list for {type_name(typ)}"
        )
    elif unpacks == 1:
        expected_count = len(type_params) - 1
        expected_msg = f"at least {len(type_params) - 1}"
    else:
        expected_count = len(type_params)
        expected_msg = f"{expected_count}"
    args_len = len(type_args)
    if 0 < args_len < expected_count:
        raise TypeError(
            f"Too few arguments for {type_name(typ)}; "
            f"actual {args_len}, expected {expected_msg}"
        )


def _flatten_type_args(
    type_args: Sequence[Type],
    allow_ellipsis_if_many_args: bool = False,
) -> Sequence[Type]:
    result = []
    for type_arg in type_args:
        if is_unpack(type_arg):
            unpacked_type = get_args(type_arg)[0]
            if is_type_var_tuple(unpacked_type):
                result.append(type_arg)
            elif is_variable_length_tuple(unpacked_type):
                if len(type_args) == 1:
                    result.extend(_flatten_type_args(get_args(unpacked_type)))
                elif allow_ellipsis_if_many_args:
                    result.extend(_flatten_type_args(get_args(unpacked_type)))
                else:
                    result.append(type_arg)
            elif unpacked_type == Tuple[()]:
                if len(type_args) == 1:
                    result.append(())  # type: ignore
            elif (
                PEP_585_COMPATIBLE and unpacked_type == tuple[()]  # type: ignore
            ):
                if len(type_args) == 1:
                    result.append(())  # type: ignore
            else:
                result.extend(_flatten_type_args(get_args(unpacked_type)))
        else:
            result.append(type_arg)
    return result


def resolve_type_params(
    typ: Type,
    type_args: Sequence[Type] = (),
    include_bases: bool = True,
) -> Dict[Type, Dict[Type, Type]]:
    resolved_type_params: Dict[Type, Type] = {}
    result = {typ: resolved_type_params}
    type_params = []

    for base in get_orig_bases(typ):
        base_type_params = collect_type_params(base)
        for type_param in base_type_params:
            if type_param not in type_params:
                type_params.append(type_param)

    _check_generic(typ, type_params, type_args)

    type_args = _flatten_type_args(type_args, allow_ellipsis_if_many_args=True)
    param_idx = 0
    unpack_param_idx = -1
    arg_idx = 0
    while param_idx < len(type_params):
        type_param = type_params[param_idx]
        if not is_unpack(type_param):
            if type_param not in resolved_type_params:
                try:
                    next_type_arg = type_args[arg_idx]
                    if next_type_arg is Ellipsis:
                        next_type_arg = type_args[arg_idx - 1]
                    else:
                        if unpack_param_idx < 0:
                            arg_idx += 1
                        else:
                            arg_idx -= 1
                except IndexError:
                    next_type_arg = type_param
                resolved_type_params[type_param] = next_type_arg
                if unpack_param_idx < 0:
                    param_idx += 1
                else:
                    param_idx -= 1
        elif unpack_param_idx < 0:
            unpack_param_idx = param_idx
            param_idx = -1
            arg_idx = -1
            unpacked_param = get_args(type_param)[0]
            for y in reversed(get_args(unpacked_param)):  # pragma: no cover
                # We turn Tuple[x,y] to x, y, but leave this here just in case
                type_params.insert(param_idx, y)
        else:
            if not type_args and is_type_var_tuple(get_args(type_param)[0]):
                resolved_type_params[type_param] = Unpack[
                    Tuple[Any, ...]  # type: ignore
                ]
                break
            t_args = type_args[unpack_param_idx : len(type_args) + arg_idx + 1]
            if len(t_args) == 1 and t_args[0] == ():
                x: Any = ()
            elif len(t_args) > 2 and t_args[-1] is Ellipsis:
                x = (*t_args[:-2], Unpack[Tuple[t_args[-2], ...]])
            else:
                x = tuple(t_args)
            resolved_type_params[type_param] = Unpack[Tuple[x]]  # type: ignore
            break

    if include_bases:
        orig_bases = {
            get_type_origin(orig_base): orig_base
            for orig_base in get_orig_bases(typ)
        }
        for base in getattr(typ, "__bases__", ()):
            orig_base = orig_bases.get(get_type_origin(base))
            base_type_params = get_args(orig_base)
            base_type_args = tuple(
                [resolved_type_params.get(a, a) for a in base_type_params]
            )
            result.update(resolve_type_params(base, base_type_args))

    return result


def substitute_type_params(typ: Type, substitutions: Dict[Type, Type]) -> Type:
    if is_annotated(typ):
        origin = get_type_origin(typ)
        subst = substitutions.get(origin, origin)
        return typing_extensions.Annotated[
            (subst, *get_type_annotations(typ))  # type: ignore
        ]
    else:
        new_type_args = []
        for type_param in collect_type_params(typ):
            new_type_args.append(substitutions.get(type_param, type_param))
        if new_type_args:
            with suppress(TypeError, KeyError):
                return typ[tuple(new_type_args)]
        if is_hashable(typ):
            return substitutions.get(typ, typ)
        else:
            return typ


def get_name_error_name(e: NameError) -> str:
    if PY_310_MIN:
        return e.name  # type: ignore
    else:
        match = re.search("'(.*)'", e.args[0])
        return match.group(1) if match else ""


def is_dialect_subclass(typ: Type) -> bool:
    try:
        return issubclass(typ, Dialect)
    except TypeError:
        return False


def is_self(typ: Type) -> bool:
    return typ is typing_extensions.Self


def is_required(typ: Type) -> bool:
    return get_type_origin(typ) is typing_extensions.Required  # noqa


def is_not_required(typ: Type) -> bool:
    return get_type_origin(typ) is typing_extensions.NotRequired  # noqa


def get_function_arg_annotation(
    function: typing.Callable[..., Any],
    arg_name: typing.Optional[str] = None,
    arg_pos: typing.Optional[int] = None,
) -> typing.Type:
    parameters = inspect.signature(function).parameters
    if arg_name is not None:
        parameter = parameters[arg_name]
    elif arg_pos is not None:
        parameter = parameters[list(parameters.keys())[arg_pos]]
    else:
        raise ValueError("arg_name or arg_pos must be passed")
    annotation = parameter.annotation
    if annotation is inspect.Signature.empty:
        raise ValueError(f"Argument {arg_name} doesn't have annotation")
    if isinstance(annotation, str):
        annotation = str_to_forward_ref(
            annotation, inspect.getmodule(function)
        )
    return annotation


def get_function_return_annotation(
    function: typing.Callable[[typing.Any], typing.Any]
) -> typing.Type:
    annotation = inspect.signature(function).return_annotation
    if annotation is inspect.Signature.empty:
        raise ValueError("Function doesn't have return annotation")
    if isinstance(annotation, str):
        annotation = str_to_forward_ref(
            annotation, inspect.getmodule(function)
        )
    return annotation


def is_unpack(typ: Type) -> bool:
    for module in (typing, typing_extensions):
        with suppress(AttributeError):
            if get_type_origin(typ) is getattr(module, "Unpack"):
                return True
    return False


def is_type_var_tuple(typ: Type) -> bool:
    for module in (typing, typing_extensions):
        with suppress(AttributeError):
            if type(typ) is getattr(module, "TypeVarTuple"):
                return True
    return False


def is_variable_length_tuple(typ: Type) -> bool:
    type_args = get_args(typ)
    return len(type_args) == 2 and type_args[1] is Ellipsis


def hash_type_args(type_args: typing.Iterable[typing.Type]) -> str:
    return md5(",".join(map(type_name, type_args)).encode()).hexdigest()


def iter_all_subclasses(cls: Type) -> typing.Iterator[Type]:
    for subclass in cls.__subclasses__():
        yield subclass
        yield from iter_all_subclasses(subclass)


def is_hashable(value: Any) -> bool:
    try:
        hash(value)
        return True
    except TypeError:
        return False


def is_hashable_type(typ: Any) -> bool:
    try:
        return issubclass(typ, typing.Hashable)
    except TypeError:
        return True


def str_to_forward_ref(
    annotation: str, module: Optional[types.ModuleType] = None
) -> ForwardRef:
    if PY_39_MIN:
        return ForwardRef(annotation, module=module)  # type: ignore
    else:
        return ForwardRef(annotation)


def evaluate_forward_ref(
    typ: ForwardRef, globalns: Any, localns: Any
) -> Optional[Type]:
    if PY_39_MIN:
        return typ._evaluate(
            globalns, localns, recursive_guard=frozenset()
        )  # type: ignore[call-arg]
    else:
        return typ._evaluate(globalns, localns)  # type: ignore[call-arg]


def get_forward_ref_referencing_globals(
    referenced_type: typing.ForwardRef,
    referencing_object: Optional[Any] = None,
    fallback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if fallback is None:
        fallback = {}
    forward_module = getattr(referenced_type, "__forward_module__", None)
    if not forward_module and referencing_object:
        # We can't get the module in which ForwardRef's value is defined on
        # Python < 3.10, ForwardRef evaluation might not work properly
        # without this information, so we will consider the namespace of
        # the module in which this ForwardRef is used as globalns.
        return getattr(
            sys.modules.get(referencing_object.__module__, None),
            "__dict__",
            fallback,
        )
    else:
        return getattr(forward_module, "__dict__", fallback)


def is_type_alias_type(typ: Type) -> bool:
    if PY_312_MIN:
        return isinstance(typ, typing.TypeAliasType)  # type: ignore
    else:
        return False


def type_var_has_default(typ: Any) -> bool:
    try:
        return typ.has_default()
    except AttributeError:
        return getattr(typ, "__default__", None) is not None


def get_type_var_default(typ: Any) -> Type:
    return getattr(typ, "__default__")
