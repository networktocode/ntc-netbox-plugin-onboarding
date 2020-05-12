from django.db import models
from django.contrib.auth.models import User
from .choices import OnboardingStatusChoices, OnboardingFailChoices


class OnboardingTask(models.Model):
    """
    The status of each onboarding Task is tracked in the OnboardingTask table
    """

    group_id = models.CharField(max_length=255, help_text="CSV Bulk Import Group ID (optional)", blank=True)

    owner = models.ForeignKey(
        to=User, on_delete=models.SET_NULL, help_text="CSV Bulk Task Owner (optional)", blank=True, null=True
    )

    created_device = models.ForeignKey(to="dcim.Device", on_delete=models.SET_NULL, blank=True, null=True)

    ip_address = models.CharField(max_length=255, help_text="primary ip address for the device", null=True)

    site = models.ForeignKey(to="dcim.Site", on_delete=models.SET_NULL, blank=True, null=True)

    username = models.CharField(max_length=255, help_text="Device Username (optional)", blank=True)

    password = models.CharField(max_length=255, help_text="Device Password (optional)", blank=True)

    secret = models.CharField(max_length=255, help_text="Device Secret Password (optional)", blank=True)

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
        "username",
        "password",
        "secret",
        "port",
        "timeout",
        "platform",
        "role",
    ]

    class Meta:
        ordering = ["created_on"]
