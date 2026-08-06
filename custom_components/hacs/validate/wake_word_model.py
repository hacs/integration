from __future__ import annotations

from typing import TYPE_CHECKING

from ..enums import HacsCategory, RepositoryFile
from ..utils.json import json_loads
from .base import ActionValidationBase, ValidationException

if TYPE_CHECKING:
    from ..repositories.base import HacsRepository
    from ..repositories.wake_word import HacsWakeWordRepository


async def async_setup_validator(repository: HacsRepository) -> Validator:
    """Set up this validator."""
    return Validator(repository=repository)


class Validator(ActionValidationBase):
    """Validate the wake word model repository."""

    repository: HacsWakeWordRepository

    categories = (HacsCategory.WAKE_WORD,)

    async def async_validate(self) -> None:
        """Validate the repository.

        Home Assistant's own loader is intentionally permissive so users can drag
        files into custom_wake_words/. A published HACS repository is a curated,
        single-purpose artifact, so a stricter shape is enforced here: exactly one
        config (manifest) file and exactly one model file, sharing the same stem,
        with the config's "model" value naming that model file (e.g.
        "my_wake_word.json" + "my_wake_word.tflite" where the config contains
        {"model": "my_wake_word.tflite"}).
        """
        content_path = (
            "" if self.repository.repository_manifest.content_in_root else "custom_wake_words"
        )
        location = f"'{content_path}/'" if content_path else "the repository root"

        # Files located directly in the content directory (not nested deeper).
        treefiles = [
            treefile
            for treefile in self.repository.tree
            if not treefile.is_directory and treefile.path == content_path
        ]

        # A repository must ship a single flat manifest+model pair. Reject wake
        # word files nested in a subdirectory so a second model cannot slip in
        # unnoticed (and so the manifest and model never end up in different
        # directories). Skipped for content_in_root, where there is no subtree.
        if content_path:
            nested = sorted(
                treefile.full_path
                for treefile in self.repository.tree
                if not treefile.is_directory
                and treefile.path.startswith(f"{content_path}/")
                and (
                    treefile.filename.endswith(".tflite")
                    or treefile.filename.endswith(".json")
                )
            )
            if nested:
                raise ValidationException(
                    f"Wake word files must be directly in '{content_path}/', "
                    f"not in a subdirectory: {', '.join(nested)}"
                )

        # Locate the config (manifest) file. hacs.json is repository metadata, not
        # a wake word config, so it is ignored even when content_in_root is set.
        config_files = [
            treefile
            for treefile in treefiles
            if treefile.filename.endswith(".json")
            and treefile.filename != RepositoryFile.HACS_JSON
        ]
        if len(config_files) == 0:
            raise ValidationException(f"No wake word config (.json) file found in {location}")
        if len(config_files) > 1:
            raise ValidationException(
                f"Expected exactly one wake word config (.json) file in {location}, "
                f"found {len(config_files)}: {', '.join(sorted(f.filename for f in config_files))}"
            )

        config_file = config_files[0]
        stem = config_file.filename.removesuffix(".json")
        expected_model = f"{stem}.tflite"

        # Locate the model file. Exactly one is required so there is no ambiguity
        # about which model this repository ships.
        model_files = [
            treefile.filename for treefile in treefiles if treefile.filename.endswith(".tflite")
        ]
        if len(model_files) == 0:
            raise ValidationException(f"No wake word model (.tflite) file found in {location}")
        if len(model_files) > 1:
            raise ValidationException(
                f"Expected exactly one wake word model (.tflite) file in {location}, "
                f"found {len(model_files)}: {', '.join(sorted(model_files))}"
            )

        # The config and model files must share the same stem.
        model_filename = model_files[0]
        if model_filename != expected_model:
            raise ValidationException(
                f"The config '{config_file.filename}' and model '{model_filename}' must share "
                f"the same name; expected the model to be named '{expected_model}'"
            )

        # Inspect the config file.
        content = await self.repository.get_documentation(
            filename=config_file.full_path, version=self.repository.ref
        )
        if content is None:
            raise ValidationException(f"Could not read '{config_file.full_path}'")
        try:
            config = json_loads(content)
        except ValueError as exception:
            raise ValidationException(
                f"'{config_file.filename}' is not valid JSON: {exception}"
            ) from exception
        if not isinstance(config, dict):
            raise ValidationException(f"'{config_file.filename}' must contain a JSON object")

        # Required keys, mirroring Home Assistant's wake word config schema.
        for key in ("type", "wake_word", "model"):
            if key not in config:
                raise ValidationException(
                    f"'{config_file.filename}' is missing the required '{key}' key"
                )

        # The "model" value must name the model file exactly.
        if config["model"] != expected_model:
            raise ValidationException(
                f"'{config_file.filename}' declares model '{config['model']}', "
                f"but it must be '{expected_model}' to match the config file name"
            )
