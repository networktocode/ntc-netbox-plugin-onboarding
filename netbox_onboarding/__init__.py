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

__version__ = "1.0.0"

from extras.plugins import PluginConfig


class OnboardingConfig(PluginConfig):
    """Plugin configuration for the netbox_onboarding plugin."""

    name = "netbox_onboarding"
    verbose_name = "Plugin for Easy Device Onboarding"
    version = "1.0.0"
    author = "Network to Code"
    description = ""
    base_url = "onboarding"
    required_settings = []
    default_settings = {}
    caching_config = {}


config = OnboardingConfig  # pylint:disable=invalid-name
