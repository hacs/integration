'''
This namespace is here only to provide compatibility with 0.6.x

It will be removed in 0.8.x
'''

import sys
import warnings

# load pyroute2 entry points
import pyroute2  # noqa: F401

warnings.warn(
    'pr2modules namespace is deprecated, use pyroute2 instead',
    DeprecationWarning,
)

# alias every `pyroute2` entry, in addition to the block above
#
# Bug-Url: https://github.com/svinota/pyroute2/issues/913
#
for key, value in list(sys.modules.items()):
    if key.startswith("pyroute2."):
        sys.modules[key.replace("pyroute2", "pr2modules")] = value
