"""Model serializers for the netbox_onboarding REST API.

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

from rest_framework import serializers
from django_rq import get_queue

from dcim.models import Site, DeviceRole, Platform

from netbox_onboarding.models import OnboardingTask
from netbox_onboarding.utils.credentials import Credentials


class OnboardingTaskSerializer(serializers.ModelSerializer):
    """Serializer for the OnboardingTask model."""

    site = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        queryset=Site.objects.all(),
        slug_field="slug",
        required=True,
        help_text="NetBox site 'slug' value",
    )

    ip_address = serializers.CharField(required=True, help_text="IP Address to reach device",)

    username = serializers.CharField(required=False, write_only=True, help_text="Device username",)

    password = serializers.CharField(required=False, write_only=True, help_text="Device password",)

    secret = serializers.CharField(required=False, write_only=True, help_text="Device secret password",)

    port = serializers.IntegerField(required=False, help_text="Device PORT to check for online")

    timeout = serializers.IntegerField(required=False, help_text="Timeout (sec) for device connect")

    role = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        queryset=DeviceRole.objects.all(),
        slug_field="slug",
        required=False,
        help_text="NetBox device role 'slug' value",
    )

    device_type = serializers.CharField(required=False, help_text="NetBox device type 'slug' value",)

    platform = serializers.SlugRelatedField(
        many=False,
        read_only=False,
        queryset=Platform.objects.all(),
        slug_field="slug",
        required=False,
        help_text="NetBox Platform 'slug' value",
    )

    created_device = serializers.CharField(required=False, read_only=True, help_text="Created device name",)

    status = serializers.CharField(required=False, read_only=True, help_text="Onboarding Status")

    failed_reason = serializers.CharField(required=False, read_only=True, help_text="Failure reason")

    message = serializers.CharField(required=False, read_only=True, help_text="Status message")

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = [
            "id",
            "site",
            "ip_address",
            "username",
            "password",
            "secret",
            "port",
            "timeout",
            "role",
            "device_type",
            "platform",
            "created_device",
            "status",
            "failed_reason",
            "message",
        ]

    def create(self, validated_data):
        """Create an OnboardingTask and enqueue it for processing."""
        # Fields are string-type so default to empty (instead of None)
        username = validated_data.pop("username", "")
        password = validated_data.pop("password", "")
        secret = validated_data.pop("secret", "")

        credentials = Credentials(username=username, password=password, secret=secret,)

        ot = OnboardingTask.objects.create(**validated_data)

        webhook_queue = get_queue("default")

        webhook_queue.enqueue("netbox_onboarding.worker.onboard_device", ot.id, credentials)

        return ot
