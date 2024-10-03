"""Base types and internal models."""

from abc import ABC
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Literal

from mashumaro import DataClassDictMixin
from mashumaro.config import BaseConfig
from mashumaro.mixins.orjson import DataClassORJSONMixin


class SentinelMeta(type):
    """Metaclass for sentinel to improve representation and make falsy.

    Credit to https://stackoverflow.com/a/69243488 .
    """

    def __repr__(cls) -> str:
        """Represent class more like an enum."""
        return f"<{cls.__name__}>"

    def __bool__(cls) -> Literal[False]:
        """Return false as a sentinel is akin to an empty value."""
        return False


class DEFAULT(metaclass=SentinelMeta):
    """Sentinel for default value when None is valid."""


class RequestConfig(BaseConfig):
    """Default Mashumaro config for all request models."""

    omit_default = True


@dataclass(frozen=True)
class Request(ABC, DataClassDictMixin):
    """Omit default in requests to allow Supervisor to set default.

    If None is a valid value, the default value should be the sentinel
    DEFAULT for optional fields.
    """

    class Config(RequestConfig):
        """Mashumaro config."""


@dataclass(frozen=True)
class Options(ABC, DataClassDictMixin):
    """Superclass for Options models to ensure a field is present.

    All fields should be optional. If None is a valid value, use the DEFAULT
    sentinel. Client should only pass changed fields to Supervisor.
    """

    def __post_init__(self) -> None:
        """Validate at least one field is present."""
        if not self.to_dict():
            raise TypeError("At least one field must have a value")

    class Config(RequestConfig):
        """Mashumaro config."""


@dataclass(frozen=True)
class ResponseData(ABC, DataClassDictMixin):
    """Superclass for all response data objects."""


class ResultType(StrEnum):
    """ResultType type."""

    OK = "ok"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Response(DataClassORJSONMixin):
    """Response model for all JSON based endpoints."""

    result: ResultType
    data: Any | None = None
    message: str | None = None
    job_id: str | None = None
