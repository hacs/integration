"""Initialize repositories."""
from custom_components.hacs.repositories.theme import HacsTheme
from custom_components.hacs.repositories.integration import HacsIntegration
from custom_components.hacs.repositories.python_script import HacsPythonScript
from custom_components.hacs.repositories.appdaemon import HacsAppdaemon
from custom_components.hacs.repositories.netdaemon import HacsNetdaemon
from custom_components.hacs.repositories.plugin import HacsPlugin

RERPOSITORY_CLASSES = {
    "theme": HacsTheme,
    "integration": HacsIntegration,
    "python_script": HacsPythonScript,
    "appdaemon": HacsAppdaemon,
    "netdaemon": HacsNetdaemon,
    "plugin": HacsPlugin,
}
