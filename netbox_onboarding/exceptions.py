"""Onboarding exception handling."""


class OnboardException(Exception):
    """A failure occurred during the onboarding process.

    The exception includes a reason "slug" as defined below as well as a humanized message.
    """

    REASONS = (
        "fail-config",  # config provided is not valid
        "fail-connect",  # device is unreachable at IP:PORT
        "fail-execute",  # unable to execute device/API command
        "fail-login",  # bad username/password
        "fail-dns",  # failed to get IP address from name resolution
        "fail-general",  # other error
    )

    def __init__(self, reason, message, **kwargs):
        """Init of the Onboarding exception types."""
        super(OnboardException, self).__init__(kwargs)
        self.reason = reason
        self.message = message

    def __str__(self):
        """String representation of Exception."""
        return f"{self.__class__.__name__}: {self.reason}: {self.message}"
