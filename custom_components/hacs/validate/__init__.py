from __future__ import annotations

import asyncio
import glob
import importlib
from os.path import dirname, join, sep
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from ..share import SHARE

if TYPE_CHECKING:
    from ..base import HacsBase
    from ..repositories.base import HacsRepository


def _initialize_rules():
    rules = glob.glob(join(dirname(__file__), "**/*.py"))
    for rule in rules:
        rule = rule.replace(sep, "/")
        rule = rule.split("custom_components/hacs")[-1]
        rule = f"custom_components/hacs{rule}".replace("/", ".")[:-3]
        importlib.import_module(rule)


async def async_initialize_rules(hass: HomeAssistant) -> None:
    await hass.async_add_executor_job(_initialize_rules)


async def async_run_repository_checks(hacs: HacsBase, repository: HacsRepository):
    if not SHARE["rules"]:
        await async_initialize_rules(hacs.hass)
    if not hacs.system.running:
        return
    checks = []
    for check in SHARE["rules"].get("common", []):
        checks.append(check(repository))
    for check in SHARE["rules"].get(repository.data.category, []):
        checks.append(check(repository))

    await asyncio.gather(
        *[
            check._async_run_check()
            for check in checks or []
            if hacs.system.action or not check.action_only
        ]
    )

    total = len([x for x in checks if hacs.system.action or not x.action_only])
    failed = len([x for x in checks if x.failed])

    if failed != 0:
        repository.logger.error("%s %s/%s checks failed", repository, failed, total)
        if hacs.system.action:
            exit(1)
    else:
        repository.logger.debug("%s All (%s) checks passed", repository, total)
