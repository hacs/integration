"""Utils to validate."""


def value_is_base16(value: str) -> bool:
    """Check if a value is base16."""
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
