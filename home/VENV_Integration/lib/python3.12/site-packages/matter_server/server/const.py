"""Server-only constants for the Python Matter Server."""

import pathlib
from typing import Final

# The minimum schema version (of a client) the server can support
MIN_SCHEMA_VERSION = 9

# schema version of our data model
# only bump if the format of the data in MatterNodeData changed
# and a full re-interview is mandatory
DATA_MODEL_SCHEMA_VERSION = 6

# Keep default location inherited from early version of the Python
# bindings.
DEFAULT_PAA_ROOT_CERTS_DIR: Final[pathlib.Path] = (
    pathlib.Path(__file__)
    .parent.resolve()
    .parent.resolve()
    .parent.resolve()
    .joinpath("credentials/development/paa-root-certs")
)

DEFAULT_OTA_PROVIDER_DIR: Final[pathlib.Path] = pathlib.Path().cwd().joinpath("updates")
