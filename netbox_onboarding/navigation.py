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

menu_items = (
    PluginMenuItem(
        link="plugins:netbox_onboarding:onboarding_task_list",
        link_text="Onboarding Tasks",
        permissions=["netbox_onboarding.view_onboardingtask"],
        buttons=(
            PluginMenuButton(
                link="plugins:netbox_onboarding:onboarding_task_add",
                title="Onboard",
                icon_class="fa fa-plus",
                color=ButtonColorChoices.GREEN,
                permissions=["netbox_onboarding.add_onboardingtask"],
            ),
            PluginMenuButton(
                link="plugins:netbox_onboarding:onboarding_task_import",
                title="Bulk Onboard",
                icon_class="fa fa-download",
                color=ButtonColorChoices.BLUE,
                permissions=["netbox_onboarding.add_onboardingtask"],
            ),
        ),
    ),
)
