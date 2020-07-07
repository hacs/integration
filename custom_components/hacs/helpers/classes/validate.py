class Validate:
    """Validate."""

    errors = []

    @property
    def success(self):
        """Return bool if the validation was a success."""
        if self.errors:
            return False
        return True
