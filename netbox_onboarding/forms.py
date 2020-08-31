"""Forms for network device onboarding.

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

from django import forms
from django.db import transaction
from django_rq import get_queue

from utilities.forms import BootstrapMixin, CSVModelForm
from dcim.models import Site, Platform, DeviceRole, DeviceType

from .models import OnboardingTask
from .choices import OnboardingStatusChoices, OnboardingFailChoices
from .utils.credentials import Credentials

BLANK_CHOICE = (("", "---------"),)


class OnboardingTaskForm(BootstrapMixin, forms.ModelForm):
    """Form for creating a new OnboardingTask instance."""

    ip_address = forms.CharField(
        required=True, label="IP address", help_text="IP Address/DNS Name of the device to onboard"
    )

    site = forms.ModelChoiceField(required=True, queryset=Site.objects.all())

    username = forms.CharField(required=False, help_text="Device username (will not be stored in database)")
    password = forms.CharField(
        required=False, widget=forms.PasswordInput, help_text="Device password (will not be stored in database)"
    )
    secret = forms.CharField(
        required=False, widget=forms.PasswordInput, help_text="Device secret (will not be stored in database)"
    )

    platform = forms.ModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Device platform. Define ONLY to override auto-recognition of platform.",
    )
    role = forms.ModelChoiceField(
        queryset=DeviceRole.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Device role. Define ONLY to override auto-recognition of role.",
    )
    device_type = forms.ModelChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Device type. Define ONLY to override auto-recognition of type.",
    )

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = [
            "site",
            "ip_address",
            "port",
            "timeout",
            "username",
            "password",
            "secret",
            "platform",
            "role",
            "device_type",
        ]

    def save(self, commit=True, **kwargs):
        """Save the model, and add it and the associated credentials to the onboarding worker queue."""
        model = super().save(commit=commit, **kwargs)
        if commit:
            credentials = Credentials(self.data.get("username"), self.data.get("password"), self.data.get("secret"))
            get_queue("default").enqueue("netbox_onboarding.worker.onboard_device", model.pk, credentials)
        return model


class OnboardingTaskFilterForm(BootstrapMixin, forms.ModelForm):
    """Form for filtering OnboardingTask instances."""

    site = forms.ModelChoiceField(queryset=Site.objects.all(), required=False, to_field_name="slug")

    platform = forms.ModelChoiceField(queryset=Platform.objects.all(), required=False, to_field_name="slug")

    status = forms.ChoiceField(choices=BLANK_CHOICE + OnboardingStatusChoices.CHOICES, required=False)

    failed_reason = forms.ChoiceField(
        choices=BLANK_CHOICE + OnboardingFailChoices.CHOICES, required=False, label="Failed Reason"
    )

    q = forms.CharField(required=False, label="Search")

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = ["q", "site", "platform", "status", "failed_reason"]


class OnboardingTaskFeedCSVForm(CSVModelForm):
    """Form for entering CSV to bulk-import OnboardingTask entries."""

    site = forms.ModelChoiceField(
        queryset=Site.objects.all(),
        required=True,
        to_field_name="slug",
        help_text="Slug of parent site",
        error_messages={"invalid_choice": "Site not found",},
    )
    ip_address = forms.CharField(required=True, help_text="IP Address of the onboarded device")
    username = forms.CharField(required=False, help_text="Username, will not be stored in database")
    password = forms.CharField(required=False, help_text="Password, will not be stored in database")
    secret = forms.CharField(required=False, help_text="Secret password, will not be stored in database")
    platform = forms.ModelChoiceField(
        queryset=Platform.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Slug of device platform. Define ONLY to override auto-recognition of platform.",
        error_messages={"invalid_choice": "Platform not found.",},
    )
    port = forms.IntegerField(required=False, help_text="Device PORT (def: 22)",)

    timeout = forms.IntegerField(required=False, help_text="Device Timeout (sec) (def: 30)",)

    role = forms.ModelChoiceField(
        queryset=DeviceRole.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Slug of device role. Define ONLY to override auto-recognition of role.",
        error_messages={"invalid_choice": "DeviceRole not found",},
    )

    device_type = forms.ModelChoiceField(
        queryset=DeviceType.objects.all(),
        required=False,
        to_field_name="slug",
        help_text="Slug of device type. Define ONLY to override auto-recognition of type.",
        error_messages={"invalid_choice": "DeviceType not found",},
    )

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = [
            "site",
            "ip_address",
            "port",
            "timeout",
            "platform",
            "role",
        ]

    def save(self, commit=True, **kwargs):
        """Save the model, and add it and the associated credentials to the onboarding worker queue."""
        model = super().save(commit=commit, **kwargs)
        if commit:
            credentials = Credentials(self.data.get("username"), self.data.get("password"), self.data.get("secret"))
            transaction.on_commit(
                lambda: get_queue("default").enqueue("netbox_onboarding.worker.onboard_device", model.pk, credentials)
            )
        return model
