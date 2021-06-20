"""Initialize repositories."""
from .appdaemon import HacsAppdaemon
from .integration import HacsIntegration
from .netdaemon import HacsNetdaemon
from .plugin import HacsPlugin
from .python_script import HacsPythonScript
from .theme import HacsTheme

RERPOSITORY_CLASSES = {
    "theme": HacsTheme,
    "integration": HacsIntegration,
    "python_script": HacsPythonScript,
    "appdaemon": HacsAppdaemon,
    "netdaemon": HacsNetdaemon,
    "plugin": HacsPlugin,
}
