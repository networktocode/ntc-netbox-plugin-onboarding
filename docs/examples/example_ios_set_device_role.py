"""Example of custom onboarding class.

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

from netbox_onboarding.netbox_keeper import NetboxKeeper
from netbox_onboarding.onboarding.onboarding import Onboarding


class MyOnboardingClass(Onboarding):
    """Custom onboarding class example.

    Main purpose of this class is to access and modify the onboarding_kwargs.
    By accessing the onboarding kwargs, user gains ability to modify
    onboarding parameters before the objects are created in NetBox.

    This class adds the get_device_role method that does the static
     string comparison and returns the device role.
    """

    def run(self, onboarding_kwargs):
        """Ensures network device."""
        # Access hostname from onboarding_kwargs and get device role automatically
        device_new_role = self.get_device_role(hostname=onboarding_kwargs["netdev_hostname"])

        # Update the device role in onboarding kwargs dictionary
        onboarding_kwargs["netdev_nb_role_slug"] = device_new_role

        nb_k = NetboxKeeper(**onboarding_kwargs)
        nb_k.ensure_device()

        self.created_device = nb_k.device

    @staticmethod
    def get_device_role(hostname):
        """Returns the device role based on hostname data.

        This is a static analysis of hostname string content only
        """
        hostname_lower = hostname.lower()
        if ("rtr" in hostname_lower) or ("router" in hostname_lower):
            role = "router"
        elif ("sw" in hostname_lower) or ("switch" in hostname_lower):
            role = "switch"
        elif ("fw" in hostname_lower) or ("firewall" in hostname_lower):
            role = "firewall"
        elif "dc" in hostname_lower:
            role = "datacenter"
        else:
            role = "generic"

        return role


class OnboardingDriverExtensions:
    """This is an example of a custom onboarding driver extension.

    This extension sets the onboarding_class to MyOnboardingClass,
     which is an example class of how to access and modify the device
     role automatically through the onboarding process.
    """

    def __init__(self, napalm_device):
        """Inits the class."""
        self.napalm_device = napalm_device
        self.onboarding_class = MyOnboardingClass
        self.ext_result = None

    def get_onboarding_class(self):
        """Return onboarding class for IOS driver.

        Currently supported is Standalone Onboarding Process

        Result of this method is used by the OnboardingManager to
        initiate the instance of the onboarding class.
        """
        return self.onboarding_class

    def get_ext_result(self):
        """This method is used to store any object as a return value.

        Result of this method is passed to the onboarding class as
        driver_addon_result argument.

        :return: Any()
        """
        return self.ext_result
