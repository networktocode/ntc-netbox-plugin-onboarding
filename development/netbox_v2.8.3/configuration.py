"""NetBox configuration file overrides specific to version 2.8.3."""
from .base_configuration import *  # pylint: disable=relative-beyond-top-level, wildcard-import

# Overrides specific to this version go here
REMOTE_AUTH_BACKEND = "utilities.auth_backends.RemoteUserBackend"
REMOTE_AUTH_DEFAULT_PERMISSIONS = []
REDIS["caching"]["DEFAULT_TIMEOUT"] = 300  # pylint: disable=undefined-variable
REDIS["tasks"]["DEFAULT_TIMEOUT"] = 300  # pylint: disable=undefined-variable
