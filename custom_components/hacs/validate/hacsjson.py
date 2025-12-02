from __future__ import annotations

from voluptuous.error import Invalid
from voluptuous.humanize import humanize_error

from ..enums import HacsCategory, RepositoryFile
from ..repositories.base import HacsManifest, HacsRepository
from ..utils.validate import HACS_MANIFEST_JSON_SCHEMA
from .base import ActionValidationBase, ValidationException


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the repository."""

    more_info = "https://hacs.xyz/docs/publish/include#check-hacs-manifest"

    async def async_validate(self) -> None:
        """Validate the repository."""
        if RepositoryFile.HACS_JSON not in [x.filename for x in self.repository.tree]:
            raise ValidationException(f"The repository has no '{RepositoryFile.HACS_JSON}' file")

        rawhacsjson = await self.repository.get_hacs_json_raw(version=self.repository.ref)
        if rawhacsjson is None:
            raise ValidationException(
                f"The repository has an invalid '{RepositoryFile.HACS_JSON}' file"
            )

        try:
            hacsjson = HacsManifest.from_dict(HACS_MANIFEST_JSON_SCHEMA(rawhacsjson))
        except Invalid as exception:
            self.repository.logger.warning(
                "HACS JSON validation failed for: %s",
                rawhacsjson,
            )
            raise ValidationException(humanize_error(rawhacsjson, exception)) from exception

        if self.repository.data.category == HacsCategory.INTEGRATION:
            if hacsjson.zip_release and not hacsjson.filename:
                raise ValidationException("zip_release is True, but filename is not set")

        if hacsjson.supported_languages:
            tree_files = [x.filename for x in self.repository.tree]
            missing_readmes = []
            invalid_languages = []
            for lang in hacsjson.supported_languages:
                if not lang.isalpha() or len(lang) != 2:
                    invalid_languages.append(lang)
                    continue
                
                readme_path = f"README.{lang}.md"
                found = False
                for possible_path in [
                    readme_path,
                    f"README.{lang.upper()}.md",
                    f"readme.{lang}.md",
                    f"readme.{lang.upper()}.md",
                    f"README.{lang}.MD",
                    f"README.{lang.upper()}.MD",
                ]:
                    if possible_path in tree_files:
                        found = True
                        break
                if not found:
                    missing_readmes.append(lang)

            if invalid_languages:
                raise ValidationException(
                    f"supported_languages contains invalid language codes {invalid_languages}. "
                    f"Language codes must be 2-letter alphabetic codes (e.g., 'de', 'fr', 'es')."
                )
            if missing_readmes:
                raise ValidationException(
                    f"supported_languages declares languages {missing_readmes}, "
                    f"but corresponding README files (README.{{lang}}.md) were not found in the repository."
                )