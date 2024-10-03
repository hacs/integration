"""Regex utils for AwesomeVersion."""

import re
from typing import Pattern

# General purpose patterns
RE_IS_SINGLE_DIGIT = re.compile(r"^\d{1}$")
RE_DIGIT = re.compile(r"[a-z]*(\d+)[a-z]*")
RE_MODIFIER = re.compile(r"^((?:\d+\-|\d|))(([a-z]+)\.?(\d*))$")


# Version patterns
RE_CALVER = r"(\d{2}|\d{4})\.\d{1,2}?(\.?\d{1,2}?\.?)?(\.\d)?(\d*(\w+\d+)?)"
RE_SEMVER = (
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?"
)
RE_PEP440 = (
    r"([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*"  # Main segment
    r"([-_\.]?(alpha|beta|c|pre|preview|a|b|rc)(0|[1-9][0-9]*))?"  # Pre-release segment
    r"([-_\.]?(post|r|rev)(0|[1-9][0-9]*))?"  # Post-release segment
    r"([-_\.]?(d|dev)(0|[1-9][0-9]*))?"  # Development release segment
    r"(?:\+([a-z0-9]+(?:[-_\.][a-z0-9]+)*))?"  # Local version segment
)
RE_BUILDVER = r"\d+"

RE_HEXVER = r"0x[A-Fa-f0-9]+"

RE_SPECIAL_CONTAINER = r"(latest|dev|stable|beta)"
RE_SIMPLE = r"[v|V]?((\d+)(\.\d+)+)"


def compile_regex(pattern: str) -> Pattern[str]:
    """Compile a regex."""
    return re.compile(pattern)


def generate_full_string_regex(string: str) -> Pattern[str]:
    """Generate a regex that matches the full string."""
    return compile_regex(r"^" + string + r"$")
