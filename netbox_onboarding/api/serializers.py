"""
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

import re
from ipaddress import ip_address
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from dcim.models import Device, Interface, InventoryItem, Site, DeviceRole, Platform

from netbox_onboarding.models import OnboardingTask
from netbox_onboarding.utils.credentials import Credentials


def sort_by_digits(if_name: str) -> tuple:
    """
    Extract all digits from a string and return them as tuple
    Args:
      if_name:
    Returns:
      tuple of all digits in the string
    """
    find_digit = re.compile(r"\D?(\d+)\D?")
    return tuple(map(int, find_digit.findall(if_name)))


class OnboardDeviceSerializer(serializers.Serializer):
    """
    Returns a dictionary payload of validated data
    {
      "mgmt_ipadd": <IP>,
      "site": <str Site.slug>,
      "platform": <str Platform.slug>,
      "role": <str DeviceRole.slug optional>,
      "username": <str optional>,
      "password": <str secret optional>,
      "timeout": <int optional>,
      "port": <int optional>
    }
    """

    mgmt_ipaddr = serializers.CharField(required=True, help_text="primary ip address to connect to the device")
    site = serializers.CharField(required=True, help_text="Short form site code")
    platform = serializers.CharField(required=True, help_text="NetBox Platform 'slug' value")
    role = serializers.CharField(required=False, help_text="NetBox device role 'slug' value", default="unassigned")
    username = serializers.CharField(required=False, help_text="device login user-name")
    password = serializers.CharField(required=False, help_text="device login password")
    timeout = serializers.IntegerField(required=False, help_text="Timeout (sec) for device connect", default=30)
    port = serializers.IntegerField(required=False, help_text="Device PORT to check for online", default=22)

    def validate_mgmt_ipadd(self, value):
        try:
            ip_address(value)
            return value
        except ValueError:
            raise ValidationError(f"{value}: invalid IP address")

    def validate_site(self, value):
        try:
            Site.objects.get(slug=value)
        except Site.DoesNotExist:
            raise ValidationError({"errmsg": f"{value}: invalid site code (Site.slug)"})
        return value

    def validate_platform(self, value):
        try:
            Platform.objects.get(slug=value)
        except Platform.DoesNotExist:
            raise ValidationError({"errmsg": f"{value}: invalid platform (Platform.slug)"})
        return value

    def validate_role(self, value):
        if value == "unassigned":
            return value
        try:
            DeviceRole.objects.get(slug=value)
        except DeviceRole.DoesNotExist:
            raise ValidationError({"errmsg": f"{value}: invalid device role (DeviceRole.slug)"})
        return value


class OnboardingTaskSerializer(serializers.ModelSerializer):
    device = serializers.CharField(required=False, help_text="Planned device name",)

    ip_address = serializers.CharField(required=True, help_text="IP Address to reach device",)

    username = serializers.CharField(required=False, write_only=True, help_text="Device username",)

    password = serializers.CharField(required=False, write_only=True, help_text="Device password",)

    secret = serializers.CharField(required=False, write_only=True, help_text="Device secret password",)

    site = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        queryset=Site.objects.all(),
        slug_field="name",
        required=True,
        help_text="Short form site code - name",
    )

    role = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        queryset=DeviceRole.objects.all(),
        slug_field="slug",
        required=False,
        help_text="NetBox device role 'name' value",
    )

    device_type = serializers.CharField(required=False, help_text="NetBox device type 'slug' value",)

    platform = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        queryset=Platform.objects.all(),
        slug_field="slug",
        required=False,
        help_text="NetBox Platform 'name' value",
    )

    status = serializers.CharField(required=False, help_text="Onboading Status")

    failed_raison = serializers.CharField(required=False, help_text="Failure reason")

    message = serializers.CharField(required=False, help_text="NetBox Platform 'slug' value")

    port = serializers.IntegerField(required=False, help_text="Device PORT to check for online")

    timeout = serializers.IntegerField(required=False, help_text="Timeout (sec) for device connect")

    class Meta:
        model = OnboardingTask
        fields = [
            "id",
            "device",
            "ip_address",
            "username",
            "password",
            "secret",
            "site",
            "role",
            "device_type",
            "platform",
            "status",
            "failed_raison",
            "message",
            "port",
            "timeout",
        ]

    def create(self, validated_data):
        # Fields are string-type so default to empty (instead of None)
        username = validated_data.pop("username", "")
        password = validated_data.pop("password", "")
        secret = validated_data.pop("secret", "")

        credentials = Credentials(username=username, password=password, secret=secret,)

        ot = OnboardingTask.objects.create(**validated_data)

        webhook_queue = get_queue("default")

        webhook_queue.enqueue("netbox_onboarding.worker.onboard_device", ot.id, credentials)

        return ot
