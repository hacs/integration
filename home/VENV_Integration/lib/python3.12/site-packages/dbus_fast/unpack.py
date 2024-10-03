from typing import Any

from .signature import Variant


def unpack_variants(data: Any) -> Any:
    """Unpack variants and remove signature info.

    This function should only be used to unpack
    unmarshalled data as the checks are not
    idiomatic.
    """
    return _unpack_variants(data)


def _unpack_variants(data: Any) -> Any:
    if type(data) is dict:
        return {k: _unpack_variants(v) for k, v in data.items()}
    if type(data) is list:
        return [_unpack_variants(item) for item in data]
    if type(data) is Variant:
        var = data
        return _unpack_variants(var.value)
    return data
