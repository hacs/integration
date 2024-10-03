from dataclasses import dataclass


@dataclass(frozen=True)
class JSONSchemaDialect:
    uri: str
    definitions_root_pointer: str
    all_refs: bool


@dataclass(frozen=True)
class JSONSchemaDraft202012Dialect(JSONSchemaDialect):
    uri: str = "https://json-schema.org/draft/2020-12/schema"
    definitions_root_pointer: str = "#/$defs"
    all_refs: bool = False


@dataclass(frozen=True)
class OpenAPISchema31Dialect(JSONSchemaDialect):
    uri: str = "https://spec.openapis.org/oas/3.1/dialect/base"
    definitions_root_pointer: str = "#/components/schemas"
    all_refs: bool = True


DRAFT_2020_12 = JSONSchemaDraft202012Dialect()
OPEN_API_3_1 = OpenAPISchema31Dialect()


__all__ = ["JSONSchemaDialect", "DRAFT_2020_12", "OPEN_API_3_1"]
