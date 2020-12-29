"""Plugin additions to the NetBox navigation menu.

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

from extras.plugins import PluginMenuButton, PluginMenuItem
from utilities.choices import ButtonColorChoices

from .release import NETBOX_RELEASE_CURRENT, NETBOX_RELEASE_210

menu_items = (
    PluginMenuItem(
        link="plugins:netbox_onboarding:onboardingtask_list",
        link_text="Onboarding Tasks",
        permissions=["netbox_onboarding.view_onboardingtask"],
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_onboarding:onboardingtask_add",
                title="Onboard",
                icon_class="mdi mdi-plus-thick" if NETBOX_RELEASE_CURRENT >= NETBOX_RELEASE_210 else "fa fa-plus",
                color=ButtonColorChoices.GREEN,
                permissions=["netbox_onboarding.add_onboardingtask"],
            ),
            PluginMenuButton(
                link="plugins:netbox_onboarding:onboardingtask_import",
                title="Bulk Onboard",
                icon_class="mdi mdi-database-import-outline"
                if NETBOX_RELEASE_CURRENT >= NETBOX_RELEASE_210
                else "fa fa-download",
                color=ButtonColorChoices.BLUE,
                permissions=["netbox_onboarding.add_onboardingtask"],
            ),
        ),
    ),
)
