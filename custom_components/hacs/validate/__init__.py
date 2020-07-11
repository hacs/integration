import asyncio
import glob
import importlib
import inspect

from custom_components.hacs.share import get_hacs


RULES = {}


async def async_run_repository_checks(repository):
    hacs = get_hacs()
    if not hacs.system.running:
        return
    if not RULES:
        repository.logger.info("loading checks")
        await hacs.hass.async_add_executor_job(load_repository_checks)
    checks = []
    for check in RULES.get("common", []):
        checks.append(check(repository))
    for check in RULES.get(repository.data.category, []):
        checks.append(check(repository))

    await asyncio.gather(*[check._async_run_check() for check in checks or []])

    total = len(checks)
    failed = len([x for x in checks if x.failed])

    if failed != 0 and hacs.action:
        exit(f"::error::{failed}/{total} checks failed")
    elif failed != 0:
        repository.logger.error(f"{failed}/{total} checks failed")
    else:
        repository.logger.debug(f"All ({total}) checks passed")


def load_repository_checks():
    hacs = get_hacs()
    if not hacs.system.running:
        return
    root = "custom_components/hacs/validate/"
    files = glob.glob(f"{root}/**/*", recursive=True)
    for filename in files:
        filename = filename.replace(root, "")
        if (
            filename.startswith("__pycache__")
            or filename.endswith("check.py")
            or "__init__.py" in filename
            or filename[-3:] != ".py"
        ):
            continue

        filename = filename[:-3]
        category = filename.split("/")[0]
        if category not in RULES:
            RULES[category] = []
        module_name = root.replace("/", ".") + filename.replace("/", ".")
        module = importlib.import_module(module_name)

        for check in inspect.getmembers(module, inspect.isclass):
            check = check[1]
            base = check.__bases__[0].__name__
            if not hacs.action and base == "ActionValidationBase":
                continue
            if f"{root.replace('/', '.')}{category}" in check.__module__:
                if check in RULES[category]:
                    continue
                RULES[category].append(check)

