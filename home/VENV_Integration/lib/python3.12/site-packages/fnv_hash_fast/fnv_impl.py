from functools import partial
from typing import TYPE_CHECKING, Callable

from fnvhash import FNV1_32_INIT, FNV_32_PRIME, fnva

_FNV_SIZE = 2**32

if TYPE_CHECKING:
    fnv1a_32: Callable[[bytes], int]

fnv1a_32 = partial(
    fnva, hval_init=FNV1_32_INIT, fnv_prime=FNV_32_PRIME, fnv_size=_FNV_SIZE
)

try:
    from ._fnv_impl import (  # type: ignore[no-redef] # noqa: F811 F401
        _fnv1a_32 as fnv1a_32,
    )
except ImportError:
    pass
