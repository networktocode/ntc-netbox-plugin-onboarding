"""OnboardingTask Django model.

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
from django.db import models
from .choices import OnboardingStatusChoices, OnboardingFailChoices


class OnboardingTask(models.Model):
    """The status of each onboarding Task is tracked in the OnboardingTask table."""

    created_device = models.ForeignKey(to="dcim.Device", on_delete=models.SET_NULL, blank=True, null=True)

    ip_address = models.CharField(max_length=255, help_text="primary ip address for the device", null=True)

    site = models.ForeignKey(to="dcim.Site", on_delete=models.SET_NULL, blank=True, null=True)

    role = models.ForeignKey(to="dcim.DeviceRole", on_delete=models.SET_NULL, blank=True, null=True)

    device_type = models.CharField(
        null=True, max_length=255, help_text="Device Type extracted from the device (optional)"
    )

    platform = models.ForeignKey(to="dcim.Platform", on_delete=models.SET_NULL, blank=True, null=True)

    status = models.CharField(max_length=255, choices=OnboardingStatusChoices, help_text="Overall status of the task")

    failed_reason = models.CharField(
        max_length=255, choices=OnboardingFailChoices, help_text="Raison why the task failed (optional)", null=True
    )

    message = models.CharField(max_length=511, blank=True)

    port = models.PositiveSmallIntegerField(help_text="Port to use to connect to the device", default=22)
    timeout = models.PositiveSmallIntegerField(
        help_text="Timeout period in sec to wait while connecting to the device", default=30
    )

    created_on = models.DateTimeField(auto_now_add=True)

    csv_headers = [
        "site",
        "ip_address",
        "port",
        "timeout",
        "platform",
        "role",
    ]

    class Meta:  # noqa: D106 "missing docstring in public nested class"
        ordering = ["created_on"]

    def __str__(self):
        """String representation of an OnboardingTask."""
        return f"{self.site} : {self.ip_address}"
