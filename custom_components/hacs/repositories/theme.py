"""Class for themes in HACS."""
from .repository import HacsRepository, register_repository_class


@register_repository_class
class HacsTheme(HacsRepository):
    """Themes in HACS."""

    category = "theme"

    def __init__(self, full_name):
        """Initialize."""
        super().__init__()
        self.information.full_name = full_name
        self.information.category = self.category

    async def validate_repository(self):
        """Validate."""
        await self.common_validate()

        if self.validate.errors:
            for error in self.validate.errors:
                if not self.common.status.startup:
                    self.logger.error(error)
        return self.validate.success

    async def registration(self):
        """Registration."""
        await self.common_registration()
