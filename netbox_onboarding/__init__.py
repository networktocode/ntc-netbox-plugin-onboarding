"""Plugin declaration for netbox_onboarding.

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

__version__ = "2.2.0"

from extras.plugins import PluginConfig


class OnboardingConfig(PluginConfig):
    """Plugin configuration for the netbox_onboarding plugin."""

    name = "netbox_onboarding"
    verbose_name = "Device Onboarding"
    version = __version__
    author = "Network to Code"
    description = "A plugin for NetBox to easily onboard new devices."
    base_url = "onboarding"
    required_settings = []
    min_version = "2.8.1"
    max_version = "2.11.99"
    default_settings = {
        "create_platform_if_missing": True,
        "create_manufacturer_if_missing": True,
        "create_device_type_if_missing": True,
        "create_device_role_if_missing": True,
        "default_device_role": "network",
        "default_device_role_color": "FF0000",
        "default_management_interface": "PLACEHOLDER",
        "default_management_prefix_length": 0,
        "default_device_status": "active",
        "create_management_interface_if_missing": True,
        "skip_device_type_on_update": False,
        "skip_manufacturer_on_update": False,
        "platform_map": {},
        "onboarding_extensions_map": {"ios": "netbox_onboarding.onboarding_extensions.ios",},
        "object_match_strategy": "loose",
    }
    caching_config = {}


config = OnboardingConfig  # pylint:disable=invalid-name
