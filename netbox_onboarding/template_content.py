"""Onboarding template content.

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

from extras.plugins import PluginTemplateExtension
from .models import OnboardingDevice


class DeviceContent(PluginTemplateExtension):  # pylint: disable=abstract-method
    """Table to show onboarding details on Device objects."""

    model = "dcim.device"

    def right_page(self):
        """Show table on right side of view."""
        onboarding = OnboardingDevice.objects.filter(device=self.context["object"]).first()

        if not onboarding or not onboarding.enabled:
            return ""

        status = onboarding.status
        last_check_attempt_date = onboarding.last_check_attempt_date
        last_check_successful_date = onboarding.last_check_successful_date
        last_ot = onboarding.last_ot

        return self.render(
            "netbox_onboarding/device_onboarding_table.html",
            extra_context={
                "status": status,
                "last_check_attempt_date": last_check_attempt_date,
                "last_check_successful_date": last_check_successful_date,
                "last_ot": last_ot,
            },
        )


template_extensions = [DeviceContent]
