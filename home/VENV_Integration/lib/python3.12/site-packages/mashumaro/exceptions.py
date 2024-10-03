from typing import Any, Optional, Set, Type

from mashumaro.core.meta.helpers import type_name


class MissingField(LookupError):
    def __init__(self, field_name: str, field_type: Type, holder_class: Type):
        self.field_name = field_name
        self.field_type = field_type
        self.holder_class = holder_class

    @property
    def field_type_name(self) -> str:
        return type_name(self.field_type, short=True)

    @property
    def holder_class_name(self) -> str:
        return type_name(self.holder_class, short=True)

    def __str__(self) -> str:
        return (
            f'Field "{self.field_name}" of type {self.field_type_name}'
            f" is missing in {self.holder_class_name} instance"
        )


class ExtraKeysError(ValueError):
    def __init__(self, extra_keys: Set[str], target_type: Type):
        self.extra_keys = extra_keys
        self.target_type = target_type

    @property
    def target_class_name(self) -> str:
        return type_name(self.target_type, short=True)

    def __str__(self) -> str:
        extra_keys_str = ", ".join(k for k in self.extra_keys)
        return (
            "Serialized dict has keys that are not defined in "
            f"{self.target_class_name}: {extra_keys_str}"
        )


class UnserializableDataError(TypeError):
    pass


class UnserializableField(UnserializableDataError):
    def __init__(
        self,
        field_name: str,
        field_type: Type,
        holder_class: Type,
        msg: Optional[str] = None,
    ):
        self.field_name = field_name
        self.field_type = field_type
        self.holder_class = holder_class
        self.msg = msg

    @property
    def field_type_name(self) -> str:
        return type_name(self.field_type, short=True)

    @property
    def holder_class_name(self) -> str:
        return type_name(self.holder_class, short=True)

    def __str__(self) -> str:
        s = (
            f'Field "{self.field_name}" of type {self.field_type_name} '
            f"in {self.holder_class_name} is not serializable"
        )
        if self.msg:
            s += f": {self.msg}"
        return s


class UnsupportedSerializationEngine(UnserializableField):
    def __init__(
        self,
        field_name: str,
        field_type: Type,
        holder_class: Type,
        engine: Any,
    ):
        super(UnsupportedSerializationEngine, self).__init__(
            field_name,
            field_type,
            holder_class,
            msg=f'Unsupported serialization engine "{engine}"',
        )


class UnsupportedDeserializationEngine(UnserializableField):
    def __init__(
        self,
        field_name: str,
        field_type: Type,
        holder_class: Type,
        engine: Any,
    ):
        super(UnsupportedDeserializationEngine, self).__init__(
            field_name,
            field_type,
            holder_class,
            msg=f'Unsupported deserialization engine "{engine}"',
        )


class InvalidFieldValue(ValueError):
    def __init__(
        self,
        field_name: str,
        field_type: Type,
        field_value: Any,
        holder_class: Type,
        msg: Optional[str] = None,
    ):
        self.field_name = field_name
        self.field_type = field_type
        self.field_value = field_value
        self.holder_class = holder_class
        self.msg = msg

    @property
    def field_type_name(self) -> str:
        return type_name(self.field_type, short=True)

    @property
    def holder_class_name(self) -> str:
        return type_name(self.holder_class, short=True)

    def __str__(self) -> str:
        s = (
            f'Field "{self.field_name}" of type {self.field_type_name} '
            f"in {self.holder_class_name} has invalid value "
            f"{repr(self.field_value)}"
        )
        if self.msg:
            s += f": {self.msg}"
        return s


class MissingDiscriminatorError(LookupError):
    def __init__(self, field_name: str):
        self.field_name = field_name

    def __str__(self) -> str:
        return f"Discriminator '{self.field_name}' is missing"


class SuitableVariantNotFoundError(ValueError):
    def __init__(
        self,
        variants_type: Type,
        discriminator_name: Optional[str] = None,
        discriminator_value: Any = None,
    ):
        self.variants_type = variants_type
        self.discriminator_name = discriminator_name
        self.discriminator_value = discriminator_value

    def __str__(self) -> str:
        s = f"{type_name(self.variants_type)} has no "
        if self.discriminator_value is not None:
            s += (
                f"subtype with attribute '{self.discriminator_name}' "
                f"equal to {self.discriminator_value!r}"
            )
        else:
            s += "suitable subtype"
        return s


class BadHookSignature(TypeError):
    pass


class ThirdPartyModuleNotFoundError(ModuleNotFoundError):
    def __init__(self, module_name: str, field_name: str, holder_class: Type):
        self.module_name = module_name
        self.field_name = field_name
        self.holder_class = holder_class

    @property
    def holder_class_name(self) -> str:
        return type_name(self.holder_class, short=True)

    def __str__(self) -> str:
        s = (
            f'Install "{self.module_name}" to use it as the serialization '
            f'method for the field "{self.field_name}" '
            f"in {self.holder_class_name}"
        )
        return s


class UnresolvedTypeReferenceError(NameError):
    def __init__(self, holder_class: Type, unresolved_type_name: str):
        self.holder_class = holder_class
        self.name = unresolved_type_name

    @property
    def holder_class_name(self) -> str:
        return type_name(self.holder_class, short=True)

    def __str__(self) -> str:
        return (
            f"Class {self.holder_class_name} has unresolved type reference "
            f"{self.name} in some of its fields"
        )


class BadDialect(ValueError):
    pass
