"""Onboarding module.

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


class Onboarding:
    """Generic onboarding class."""

    def __init__(self):
        """Init the class."""
        self.created_device = None
        self.credentials = None

    def run(self, onboarding_kwargs):
        """Implement run method."""
        raise NotImplementedError


class StandaloneOnboarding(Onboarding):
    """Standalone onboarding class."""

    def run(self, onboarding_kwargs):
        """Ensure device is created with NetBox Keeper."""
        nb_k = NetboxKeeper(**onboarding_kwargs)
        nb_k.ensure_device()

        self.created_device = nb_k.device
