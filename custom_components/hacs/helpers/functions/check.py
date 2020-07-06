import os
import asyncio
import glob
import importlib
import inspect


from custom_components.hacs.share import get_hacs

CHECKS = {}


async def async_run_repository_checks(repository):
    if not CHECKS:
        hass = get_hacs().hass
        repository.logger.info("loading checks")
        await hass.async_add_executor_job(load_repository_checks)
    checks = []
    for check in CHECKS.get("common", []):
        checks.append(check(repository))
    for check in CHECKS.get(repository.data.category, []):
        checks.append(check(repository))

    await asyncio.gather(*[check._async_run_check() for check in checks or []])

    total = len(checks)
    failed = len([x for x in checks if x.failed])

    if failed != 0:
        repository.logger.error(
            f"Total number of checks ({total}), number of failed checks ({failed}) for {repository.data.full_name}"
        )
    else:
        repository.logger.debug(
            f"All ({total}) checks passed for {repository.data.full_name}"
        )


def load_repository_checks():
    root = "custom_components/hacs/checks/"
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
        if category not in CHECKS:
            CHECKS[category] = []
        module_name = root.replace("/", ".") + filename.replace("/", ".")
        module = importlib.import_module(module_name)

        for check in inspect.getmembers(module, inspect.isclass):
            check = check[1]
            base = check.__bases__[0].__name__
            if "GITHUB_ACTION" not in os.environ and base == "RepositoryActionCheck":
                continue
            if f"{root.replace('/', '.')}{category}" in check.__module__:
                CHECKS[category].append(check)
