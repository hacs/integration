from dataclasses import dataclass, field


@dataclass
class Validate:
    """Validate."""

    errors: list[str] = field(default_factory=list)

    @property
    def success(self):
        """Return bool if the validation was a success."""
        return len(self.errors) == 0
