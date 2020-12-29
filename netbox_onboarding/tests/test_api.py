"""Unit tests for netbox_onboarding REST API.

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
from django.contrib.auth.models import User  # pylint: disable=imported-auth-user
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.models import Token

from dcim.models import Site


from netbox_onboarding.models import OnboardingTask


class OnboardingTaskTestCase(TestCase):
    """Test the OnboardingTask API."""

    def setUp(self):
        """Create a superuser and token for API calls."""
        self.user = User.objects.create(username="testuser", is_superuser=True)
        self.token = Token.objects.create(user=self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

        self.base_url_lookup = "plugins-api:netbox_onboarding-api:onboardingtask"

        self.site1 = Site.objects.create(name="USWEST", slug="uswest")

        self.onboarding_task1 = OnboardingTask.objects.create(ip_address="10.10.10.10", site=self.site1)
        self.onboarding_task2 = OnboardingTask.objects.create(ip_address="192.168.1.1", site=self.site1)

    def test_list_onboarding_tasks(self):
        """Verify that OnboardingTasks can be listed."""
        url = reverse(f"{self.base_url_lookup}-list")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

    def test_get_onboarding_task(self):
        """Verify that an Onboardingtask can be retrieved."""
        url = reverse(f"{self.base_url_lookup}-detail", kwargs={"pk": self.onboarding_task1.pk})

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["ip_address"], self.onboarding_task1.ip_address)
        self.assertEqual(response.data["site"], self.onboarding_task1.site.slug)

    def test_create_task_missing_mandatory_parameters(self):
        """Verify that the only mandatory POST parameters are ip_address and site."""
        url = reverse(f"{self.base_url_lookup}-list")

        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # The response tells us which fields are missing from the request
        self.assertIn("ip_address", response.data)
        self.assertIn("site", response.data)
        self.assertEqual(len(response.data), 2, "Only two parameters should be mandatory")

    def test_create_task(self):
        """Verify that an OnboardingTask can be created."""
        url = reverse(f"{self.base_url_lookup}-list")
        data = {"ip_address": "10.10.10.20", "site": self.site1.slug}

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        for key, value in data.items():
            self.assertEqual(response.data[key], value)
        self.assertEqual(response.data["port"], 22)  # default value
        self.assertEqual(response.data["timeout"], 30)  # default value

        onboarding_task = OnboardingTask.objects.get(pk=response.data["id"])
        self.assertEqual(onboarding_task.ip_address, data["ip_address"])
        self.assertEqual(onboarding_task.site, self.site1)

    def test_update_task_forbidden(self):
        """Verify that an OnboardingTask cannot be updated via this API."""
        url = reverse(f"{self.base_url_lookup}-detail", kwargs={"pk": self.onboarding_task1.pk})

        response = self.client.patch(url, {"ip_address": "10.10.10.20"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.onboarding_task1.ip_address, "10.10.10.10")

        response = self.client.put(url, {"ip_address": "10.10.10.20"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(self.onboarding_task1.ip_address, "10.10.10.10")

    def test_delete_task(self):
        """Verify that an OnboardingTask can be deleted."""
        url = reverse(f"{self.base_url_lookup}-detail", kwargs={"pk": self.onboarding_task1.pk})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        with self.assertRaises(OnboardingTask.DoesNotExist):
            OnboardingTask.objects.get(pk=self.onboarding_task1.pk)
