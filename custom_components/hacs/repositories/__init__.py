"""Initialize repositories."""
from custom_components.hacs.repositories.appdaemon import HacsAppdaemonRepository
from custom_components.hacs.repositories.integration import HacsIntegrationRepository
from custom_components.hacs.repositories.netdaemon import HacsNetdaemonRepository
from custom_components.hacs.repositories.plugin import HacsPluginRepository
from custom_components.hacs.repositories.python_script import HacsPythonScriptRepository
from custom_components.hacs.repositories.theme import HacsThemeRepository

RERPOSITORY_CLASSES = {
    "theme": HacsThemeRepository,
    "integration": HacsIntegrationRepository,
    "python_script": HacsPythonScriptRepository,
    "appdaemon": HacsAppdaemonRepository,
    "netdaemon": HacsNetdaemonRepository,
    "plugin": HacsPluginRepository,
}
