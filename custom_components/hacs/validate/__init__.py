import asyncio

from custom_components.hacs.share import get_hacs

from .appdaemon import RULES as AppDaemonRules
from .common import RULES as CommonRules
from .integration import RULES as IntegrationRules
from .netdaemon import RULES as NetDaemonRules
from .plugin import RULES as PluginRules
from .python_script import RULES as PythonScriptRules
from .theme import RULES as ThemeRules


RULES = {
    "appdaemon": AppDaemonRules,
    "common": CommonRules,
    "integration": IntegrationRules,
    "netdaemon": NetDaemonRules,
    "plugin": PluginRules,
    "python_script": PythonScriptRules,
    "theme": ThemeRules,
}


async def async_run_repository_checks(repository):
    hacs = get_hacs()
    if not hacs.system.running:
        return
    checks = []
    for check in RULES.get("common", []):
        checks.append(check(repository))
    for check in RULES.get(repository.data.category, []):
        checks.append(check(repository))

    await asyncio.gather(*[check._async_run_check() for check in checks or []])

    total = len(checks)
    failed = len([x for x in checks if x.failed])

    if failed != 0 and hacs.action:
        print(f"::error::{failed}/{total} checks failed")
        exit(f"::error::{failed}/{total} checks failed")
    elif failed != 0:
        print(f"{failed}/{total} checks failed")
        repository.logger.error(f"{failed}/{total} checks failed")
    else:
        print(f"All ({total}) checks passed")
        repository.logger.debug(f"All ({total}) checks passed")
