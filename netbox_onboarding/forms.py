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

from utilities.forms import BootstrapMixin
from dcim.models import Site, Platform, DeviceRole
from extras.forms import CustomFieldModelCSVForm

from .models import OnboardingTask
from .choices import OnboardingStatusChoices, OnboardingFailChoices

BLANK_CHOICE = (("", "---------"),)


class OnboardingTaskForm(BootstrapMixin, forms.ModelForm):
    """Form for creating a new OnboardingTask instance."""

    ip_address = forms.CharField(required=True, label="IP address", help_text="IP address of the device to onboard")

    site = forms.ModelChoiceField(required=True, queryset=Site.objects.all(), to_field_name="slug")

    username = forms.CharField(required=False, help_text="Device username (will not be stored in database)")
    password = forms.CharField(required=False, help_text="Device password (will not be stored in database)")
    secret = forms.CharField(required=False, help_text="Device secret (will not be stored in database)")

    device_type = forms.CharField(required=False, help_text="Device type slug (optional)")

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = ["ip_address", "site", "username", "password", "secret", "role", "device_type", "platform", "port", "timeout"]


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


class OnboardingTaskFeedCSVForm(CustomFieldModelCSVForm):
    """TODO document me."""

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

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = OnboardingTask.csv_headers
