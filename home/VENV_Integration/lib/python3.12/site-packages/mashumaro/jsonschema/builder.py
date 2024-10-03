from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from mashumaro.jsonschema.dialects import DRAFT_2020_12, JSONSchemaDialect
from mashumaro.jsonschema.models import Context, JSONSchema
from mashumaro.jsonschema.schema import Instance, get_schema

try:
    from mashumaro.mixins.orjson import (
        DataClassORJSONMixin as DataClassJSONMixin,
    )
except ImportError:  # pragma: no cover
    from mashumaro.mixins.json import DataClassJSONMixin  # type: ignore


def build_json_schema(
    instance_type: Type,
    context: Optional[Context] = None,
    with_definitions: bool = True,
    all_refs: Optional[bool] = None,
    with_dialect_uri: bool = False,
    dialect: Optional[JSONSchemaDialect] = None,
    ref_prefix: Optional[str] = None,
) -> JSONSchema:
    if context is None:
        context = Context()
    else:
        context = Context(
            dialect=context.dialect,
            definitions=context.definitions,
            all_refs=context.all_refs,
            ref_prefix=context.ref_prefix,
        )
    if dialect is not None:
        context.dialect = dialect
    if all_refs is not None:
        context.all_refs = all_refs
    elif context.all_refs is None:
        context.all_refs = context.dialect.all_refs
    if ref_prefix is not None:
        context.ref_prefix = ref_prefix.rstrip("/")
    elif context.ref_prefix is None:
        context.ref_prefix = context.dialect.definitions_root_pointer
    instance = Instance(instance_type)
    schema = get_schema(instance, context, with_dialect_uri=with_dialect_uri)
    if with_definitions and context.definitions:
        schema.definitions = context.definitions
    return schema


@dataclass
class JSONSchemaDefinitions(DataClassJSONMixin):
    definitions: Dict[str, JSONSchema]

    def __post_serialize__(  # type: ignore
        self, d: Dict[Any, Any]
    ) -> List[Dict[str, Any]]:
        return d["definitions"]


class JSONSchemaBuilder:
    def __init__(
        self,
        dialect: JSONSchemaDialect = DRAFT_2020_12,
        all_refs: Optional[bool] = None,
        ref_prefix: Optional[str] = None,
    ):
        if all_refs is None:
            all_refs = dialect.all_refs
        if ref_prefix is None:
            ref_prefix = dialect.definitions_root_pointer
        self.context = Context(
            dialect=dialect,
            all_refs=all_refs,
            ref_prefix=ref_prefix.rstrip("/"),
        )

    def build(self, instance_type: Type) -> JSONSchema:
        return build_json_schema(
            instance_type=instance_type,
            context=self.context,
            with_definitions=False,
        )

    def get_definitions(self) -> JSONSchemaDefinitions:
        return JSONSchemaDefinitions(self.context.definitions)


__all__ = ["JSONSchemaBuilder", "build_json_schema"]
