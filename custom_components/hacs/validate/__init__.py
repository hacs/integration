import asyncio
import importlib
import glob
from os.path import dirname, join
from custom_components.hacs.share import get_hacs, SHARE


def _initialize_rules():
    rules = glob.glob(join(dirname(__file__), "**/*.py"))
    for rule in rules:
        rule = rule.split("custom_components/hacs")[-1]
        rule = f"custom_components/hacs{rule}".replace("/", ".")[:-3]
        importlib.import_module(rule)


async def async_initialize_rules():
    hass = get_hacs().hass
    await hass.async_add_executor_job(_initialize_rules)


async def async_run_repository_checks(repository):
    hacs = get_hacs()
    if not SHARE["rules"]:
        await async_initialize_rules()
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
            if hacs.action or not check.action_only
        ]
    )

    total = len([x for x in checks if hacs.action or not x.action_only])
    failed = len([x for x in checks if x.failed])

    if failed != 0:
        repository.logger.error(f"{failed}/{total} checks failed")
        if hacs.action:
            exit(1)
    else:
        repository.logger.debug(f"All ({total}) checks passed")
