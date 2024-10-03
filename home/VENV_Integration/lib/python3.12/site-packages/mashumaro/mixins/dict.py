from typing import Any, Dict, Mapping, Type, TypeVar, final

from mashumaro.core.meta.mixin import (
    compile_mixin_packer,
    compile_mixin_unpacker,
)

__all__ = ["DataClassDictMixin"]


T = TypeVar("T", bound="DataClassDictMixin")


class DataClassDictMixin:
    __slots__ = ()

    __mashumaro_builder_params = {"packer": {}, "unpacker": {}}  # type: ignore

    def __init_subclass__(cls: Type[T], **kwargs: Any):
        super().__init_subclass__(**kwargs)
        for ancestor in cls.__mro__[-1:0:-1]:
            builder_params_ = f"_{ancestor.__name__}__mashumaro_builder_params"
            builder_params = getattr(ancestor, builder_params_, None)
            if builder_params:
                compile_mixin_unpacker(cls, **builder_params["unpacker"])
                compile_mixin_packer(cls, **builder_params["packer"])

    @final
    def to_dict(
        self: T,
        # *
        # keyword-only arguments that exist with the code generation options:
        # omit_none: bool = False
        # by_alias: bool = False
        # dialect: Type[Dialect] = None
        **kwargs: Any,
    ) -> Dict[Any, Any]: ...

    @classmethod
    @final
    def from_dict(
        cls: Type[T],
        d: Mapping,
        # *
        # keyword-only arguments that exist with the code generation options:
        # dialect: Type[Dialect] = None
        **kwargs: Any,
    ) -> T: ...

    @classmethod
    def __pre_deserialize__(
        cls: Type[T], d: Dict[Any, Any]
    ) -> Dict[Any, Any]: ...

    @classmethod
    def __post_deserialize__(cls: Type[T], obj: T) -> T: ...

    def __pre_serialize__(
        self: T,
        # context: Any = None,  # added with ADD_SERIALIZATION_CONTEXT option
    ) -> T: ...

    def __post_serialize__(
        self: T,
        d: Dict[Any, Any],
        # context: Any = None,  # added with ADD_SERIALIZATION_CONTEXT option
    ) -> Dict[Any, Any]: ...
