"""Validation utilities."""
from __future__ import annotations

from dataclasses import dataclass, field

from awesomeversion import AwesomeVersion
from homeassistant.helpers.config_validation import url as url_validator
import voluptuous as vol

from ..const import LOCALE


@dataclass
class Validate:
    """Validate."""

    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return bool if the validation was a success."""
        return len(self.errors) == 0


def _country_validator(values) -> list[str]:
    """Custom country validator."""
    countries = []
    if isinstance(values, str):
        countries.append(values.upper())
    elif isinstance(values, list):
        for value in values:
            countries.append(value.upper())
    else:
        raise vol.Invalid(f"Value '{values}' is not a string or list.", path=["country"])

    for country in countries:
        if country not in LOCALE:
            raise vol.Invalid(f"Value '{country}' is not in {LOCALE}.", path=["country"])

    return countries


HACS_MANIFEST_JSON_SCHEMA = vol.Schema(
    {
        vol.Optional("content_in_root"): bool,
        vol.Optional("country"): _country_validator,
        vol.Optional("filename"): str,
        vol.Optional("hacs"): vol.Coerce(AwesomeVersion),
        vol.Optional("hide_default_branch"): bool,
        vol.Optional("homeassistant"): vol.Coerce(AwesomeVersion),
        vol.Optional("persistent_directory"): str,
        vol.Optional("render_readme"): bool,
        vol.Optional("zip_release"): bool,
        vol.Required("name"): str,
    },
    extra=vol.PREVENT_EXTRA,
)

INTEGRATION_MANIFEST_JSON_SCHEMA = vol.Schema(
    {
        vol.Required("codeowners"): list,
        vol.Required("documentation"): url_validator,
        vol.Required("domain"): str,
        vol.Required("issue_tracker"): url_validator,
        vol.Required("name"): str,
        vol.Required("version"): vol.Coerce(AwesomeVersion),
    },
    extra=vol.ALLOW_EXTRA,
)
