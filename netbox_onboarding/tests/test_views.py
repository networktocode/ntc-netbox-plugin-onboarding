"""Unit tests for netbox_onboarding views.

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
from django.contrib.auth.models import User, Permission
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from dcim.models import Site

from netbox_onboarding.models import OnboardingTask


class OnboardingTaskListViewTestCase(TestCase):
    """Test the OnboardingTaskListView view."""

    def setUp(self):
        """Create a superuser and baseline data for testing."""
        self.user = User.objects.create(username="testuser")
        self.client = Client()
        self.client.force_login(self.user)

        self.base_url_lookup = "plugins:netbox_onboarding:"

        self.site1 = Site.objects.create(name="USWEST", slug="uswest")
        self.onboarding_task1 = OnboardingTask.objects.create(ip_address="10.10.10.10", site=self.site1)
        self.onboarding_task2 = OnboardingTask.objects.create(ip_address="192.168.1.1", site=self.site1)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_list_onboarding_tasks_anonymous(self):
        """Verify that OnboardingTasks can be listed without logging in if permissions are exempted."""
        url = reverse(f"{self.base_url_lookup}onboarding_task_list")
        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "netbox_onboarding/onboarding_tasks_list.html")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_list_onboarding_tasks(self):
        """Verify that OnboardingTasks can be listed by a user with appropriate permissions."""
        url = reverse(f"{self.base_url_lookup}onboarding_task_list")

        # Attempt to access without permissions
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Add permission
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="dcim", codename="view_device"))

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "netbox_onboarding/onboarding_tasks_list.html")


class OnboardingTaskFeedBulkImportViewTestCase(TestCase):
    """Test the OnboardingTaskFeedBulkImportView view."""

    def setUp(self):
        """Create a superuser and baseline data for testing."""
        self.user = User.objects.create(username="testuser")
        self.client = Client()
        self.client.force_login(self.user)

        self.base_url_lookup = "plugins:netbox_onboarding:"

        self.site1 = Site.objects.create(name="USWEST", slug="uswest")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_get_anonymous(self):
        """Verify that the import view cannot be seen by an anonymous user even if permissions are exempted."""
        url = reverse(f"{self.base_url_lookup}onboarding_task_import")
        self.client.logout()
        response = self.client.get(url)
        # Redirected to the login page
        self.assertEqual(response.status_code, 302)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get(self):
        """Verify that the import view can be seen by a user with appropriate permissions."""
        url = reverse(f"{self.base_url_lookup}onboarding_task_import")

        # Attempt to access without permissions
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Add permission
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="dcim", codename="add_device"))

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "utilities/obj_bulk_import.html")

    def test_post(self):
        """Verify that tasks can be bulk-imported."""
        url = reverse(f"{self.base_url_lookup}onboarding_task_import")
        csv_data = [
            "site,ip_address",
            "uswest,10.10.10.10",
            "uswest,10.10.10.20",
            "uswest,10.10.10.30",
        ]

        # Attempt to access without permissions
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # Add permission
        self.user.user_permissions.add(Permission.objects.get(content_type__app_label="dcim", codename="add_device"))

        response = self.client.post(url, data={"csv": "\n".join(csv_data)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(OnboardingTask.objects.count(), len(csv_data) - 1)
