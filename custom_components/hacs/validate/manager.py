"""Hacs validation manager."""
from __future__ import annotations

import asyncio
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from custom_components.hacs.repositories.base import HacsRepository

from .base import ValidationBase

if TYPE_CHECKING:
    from ..base import HacsBase


class ValidationManager:
    """Hacs validation manager."""

    def __init__(self, hacs: HacsBase, hass: HomeAssistant) -> None:
        """Initialize the setup manager class."""
        self.hacs = hacs
        self.hass = hass
        self._validatiors: dict[str, ValidationBase] = {}

    @property
    def validatiors(self) -> dict[str, ValidationBase]:
        """Return all list of all tasks."""
        return list(self._validatiors.values())

    async def async_load(self, repository: HacsRepository) -> None:
        """Load all tasks."""
        self._validatiors = {}
        validator_files = Path(__file__).parent
        validator_modules = (
            module.stem
            for module in validator_files.glob("*.py")
            if module.name not in ("base.py", "__init__.py", "manager.py")
        )

        async def _load_module(module: str):
            task_module = import_module(f"{__package__}.{module}")
            if task := await task_module.async_setup_validator(repository=repository):
                self._validatiors[task.slug] = task

        await asyncio.gather(*[_load_module(task) for task in validator_modules])
        self.hacs.log.debug("Loaded %s validators for %s", len(self.validatiors), repository)

    async def async_run_repository_checks(self, repository: HacsRepository) -> None:
        """Run all validators for a repository."""
        if not self.hacs.system.running:
            return

        await self.async_load(repository)

        await asyncio.gather(
            *[
                validator.execute_validation()
                for validator in self.validatiors or []
                if (self.hacs.system.action or not validator.action_only)
                and (
                    validator.category == "common" or validator.category == repository.data.category
                )
            ]
        )

        total = len([x for x in self.validatiors if self.hacs.system.action or not x.action_only])
        failed = len([x for x in self.validatiors if x.failed])

        if failed != 0:
            repository.logger.error("%s %s/%s checks failed", repository.string, failed, total)
            if self.hacs.system.action:
                exit(1)
        else:
            repository.logger.debug("%s All (%s) checks passed", repository.string, total)
