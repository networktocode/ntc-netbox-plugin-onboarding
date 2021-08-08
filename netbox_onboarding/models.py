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
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import models
from django.urls import reverse
from dcim.models import Device
from .choices import OnboardingStatusChoices, OnboardingFailChoices
from .release import NETBOX_RELEASE_CURRENT, NETBOX_RELEASE_29, NETBOX_RELEASE_211

# Support NetBox 2.8
if NETBOX_RELEASE_CURRENT < NETBOX_RELEASE_29:
    from utilities.models import ChangeLoggedModel  # pylint: disable=no-name-in-module, import-error
# Support NetBox 2.9, NetBox 2.10
elif NETBOX_RELEASE_CURRENT < NETBOX_RELEASE_211:
    from extras.models import ChangeLoggedModel  # pylint: disable=no-name-in-module, import-error
# Support NetBox 2.11
else:
    from netbox.models import ChangeLoggedModel  # pylint: disable=no-name-in-module, import-error


class OnboardingTask(ChangeLoggedModel):
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

    def __str__(self):
        """String representation of an OnboardingTask."""
        return f"{self.site} : {self.ip_address}"

    def get_absolute_url(self):
        """Provide absolute URL to an OnboardingTask."""
        return reverse("plugins:netbox_onboarding:onboardingtask", kwargs={"pk": self.pk})

    if NETBOX_RELEASE_CURRENT >= NETBOX_RELEASE_29:
        from utilities.querysets import RestrictedQuerySet  # pylint: disable=no-name-in-module, import-outside-toplevel

        objects = RestrictedQuerySet.as_manager()


class OnboardingDevice(models.Model):
    """The status of each Onboarded Device is tracked in the OnboardingDevice table."""

    device = models.OneToOneField(to="dcim.Device", on_delete=models.CASCADE)
    enabled = models.BooleanField(default=True, help_text="Whether (re)onboarding of this device is permitted")

    @property
    def last_check_attempt_date(self):
        """Date of last onboarding attempt for a device."""
        if self.device.primary_ip4:
            try:
                return (
                    OnboardingTask.objects.filter(
                        ip_address=self.device.primary_ip4.address.ip.format()  # pylint: disable=no-member
                    )
                    .latest("last_updated")
                    .created
                )
            except OnboardingTask.DoesNotExist:
                return "unknown"
        else:
            return "unknown"

    @property
    def last_check_successful_date(self):
        """Date of last successful onboarding for a device."""
        if self.device.primary_ip4:
            try:
                return (
                    OnboardingTask.objects.filter(
                        ip_address=self.device.primary_ip4.address.ip.format(),  # pylint: disable=no-member
                        status=OnboardingStatusChoices.STATUS_SUCCEEDED,
                    )
                    .latest("last_updated")
                    .created
                )
            except OnboardingTask.DoesNotExist:
                return "unknown"
        else:
            return "unknown"

    @property
    def status(self):
        """Last onboarding status."""
        if self.device.primary_ip4:
            try:
                return (
                    OnboardingTask.objects.filter(
                        ip_address=self.device.primary_ip4.address.ip.format()  # pylint: disable=no-member
                    )
                    .latest("last_updated")
                    .status
                )
            except OnboardingTask.DoesNotExist:
                return "unknown"
        else:
            return "unknown"

    @property
    def last_ot(self):
        """Last onboarding task."""
        if self.device.primary_ip4:
            try:
                return OnboardingTask.objects.filter(
                    ip_address=self.device.primary_ip4.address.ip.format()  # pylint: disable=no-member
                ).latest("last_updated")
            except OnboardingTask.DoesNotExist:
                return "unknown"
        else:
            return "unknown"


@receiver(post_save, sender=Device)
def init_onboarding_for_new_device(sender, instance, created, **kwargs):  # pylint: disable=unused-argument
    """Register to create a OnboardingDevice object for each new Device Object using Django Signal.

    https://docs.djangoproject.com/en/3.0/ref/signals/#post-save
    """
    if created:
        OnboardingDevice.objects.create(device=instance)
