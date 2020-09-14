"""Onboarding Extension for IOS.

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

from netbox_onboarding.onboarding.onboarding import StandaloneOnboarding


class OnboardingDriverExtensions:
    """Onboarding Driver's Extensions."""

    def __init__(self, napalm_device):
        """Initialize class."""
        self.napalm_device = napalm_device

    @property
    def onboarding_class(self):
        """Return onboarding class for IOS driver.

        Currently supported is Standalone Onboarding Process.

        Result of this method is used by the OnboardingManager to
        initiate the instance of the onboarding class.
        """
        return StandaloneOnboarding

    @property
    def ext_result(self):
        """This method is used to store any object as a return value.

        Result of this method is passed to the onboarding class as
        driver_addon_result argument.

        :return: Any()
        """
        return None
