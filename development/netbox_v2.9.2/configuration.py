"""NetBox configuration file overrides specific to version 2.9.2."""
from .base_configuration import *  # pylint: disable=relative-beyond-top-level, wildcard-import

REMOTE_AUTH_ENABLED = False
REMOTE_AUTH_BACKEND = "netbox.authentication.RemoteUserBackend"
REMOTE_AUTH_HEADER = "HTTP_REMOTE_USER"
REMOTE_AUTH_AUTO_CREATE_USER = True
REMOTE_AUTH_DEFAULT_GROUPS = []
REMOTE_AUTH_DEFAULT_PERMISSIONS = {}
