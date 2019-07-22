"""HACS Startup."""
from . import Hacs


class HacsStartup(Hacs):
    """Startup class."""

    async def run_startup(self):
        """Run startup tasks for HACS."""
        self.logger.critical("Startup!")
        if self.configuration.dev:
            self.logger.critical("Running in DEV mode!")
        if self.developer.devcontainer:
            self.logger.critical("Running inside a devcontainer")
            self.logger.critical("Some features have been disabled")
            self.logger.critical("It will only fetch one repository pr category")
