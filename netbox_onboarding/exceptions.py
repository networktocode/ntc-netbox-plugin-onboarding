"""Exceptions.

(c) 2020 Network To Code
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


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
        """Exception Init."""
        super(OnboardException, self).__init__(kwargs)
        self.reason = reason
        self.message = message

    def __str__(self):
        """Exception __str__."""
        return f"{self.__class__.__name__}: {self.reason}: {self.message}"
