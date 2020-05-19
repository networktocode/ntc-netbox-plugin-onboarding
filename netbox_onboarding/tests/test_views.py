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
        """Create a user and baseline data for testing."""
        self.user = User.objects.create(username="testuser")
        self.client = Client()
        self.client.force_login(self.user)

        self.url = reverse("plugins:netbox_onboarding:onboarding_task_list")

        self.site1 = Site.objects.create(name="USWEST", slug="uswest")
        self.onboarding_task1 = OnboardingTask.objects.create(ip_address="10.10.10.10", site=self.site1)
        self.onboarding_task2 = OnboardingTask.objects.create(ip_address="192.168.1.1", site=self.site1)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_list_onboarding_tasks_anonymous(self):
        """Verify that OnboardingTasks can be listed without logging in if permissions are exempted."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "netbox_onboarding/onboarding_tasks_list.html")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_list_onboarding_tasks(self):
        """Verify that OnboardingTasks can be listed by a user with appropriate permissions."""
        # Attempt to access without permissions
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

        # Add permission
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="netbox_onboarding", codename="view_onboardingtask")
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "netbox_onboarding/onboarding_tasks_list.html")


class OnboardingTaskCreateViewTestCase(TestCase):
    """Test the OnboardingTaskCreateView view."""

    def setUp(self):
        """Create a user and baseline data for testing."""
        self.user = User.objects.create(username="testuser")
        self.client = Client()
        self.client.force_login(self.user)

        self.url = reverse("plugins:netbox_onboarding:onboarding_task_add")

        self.site1 = Site.objects.create(name="USWEST", slug="uswest")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_get_anonymous(self):
        """Verify that the view cannot be accessed by anonymous users even if permissions are exempted."""
        self.client.logout()
        response = self.client.get(self.url)
        # Redirected to the login page
        self.assertEqual(response.status_code, 302)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get(self):
        """Verify that the view can be seen by a user with appropriate permissions."""
        # Attempt to access without permissions
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

        # Add permission
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="netbox_onboarding", codename="add_onboardingtask")
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "netbox_onboarding/onboarding_task_edit.html")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_post_anonymous(self):
        """Verify that the view cannot be accessed by anonymous users even if permissions are exempted."""
        self.client.logout()
        response = self.client.get(self.url)
        # Redirected to the login page
        self.assertEqual(response.status_code, 302)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_post(self):
        """Verify that the view can be used by a user with appropriate permissions."""
        # Attempt to access without permissions
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

        # Add permission
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="netbox_onboarding", codename="add_onboardingtask")
        )

        response = self.client.post(
            self.url, data={"ip_address": "10.10.10.10", "site": "uswest", "port": "22", "timeout": "30"}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OnboardingTask.objects.count(), 1)


class OnboardingTaskBulkDeleteViewTestCase(TestCase):
    """Test the OnboardingTaskBulkDeleteView view."""

    def setUp(self):
        """Create a user and baseline data for testing."""
        self.user = User.objects.create(username="testuser")
        self.client = Client()
        self.client.force_login(self.user)

        self.url = reverse("plugins:netbox_onboarding:onboarding_task_bulk_delete")

        self.site1 = Site.objects.create(name="USWEST", slug="uswest")
        self.onboarding_task1 = OnboardingTask.objects.create(ip_address="10.10.10.10", site=self.site1)
        self.onboarding_task2 = OnboardingTask.objects.create(ip_address="192.168.1.1", site=self.site1)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_post_anonymous(self):
        """Verify that the view cannot be accessed by anonymous users even if permissions are exempted."""
        self.client.logout()
        response = self.client.post(self.url)
        # Redirected to the login page
        self.assertEqual(response.status_code, 302)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_post(self):
        """Verify that the view can be seen by a user with appropriate permissions."""
        # Attempt to access without permissions
        response = self.client.post(
            self.url, data={"pk": [self.onboarding_task1.pk], "confirm": True, "_confirm": True}
        )
        self.assertEqual(response.status_code, 403)

        # Add permission
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="netbox_onboarding", codename="delete_onboardingtask")
        )

        response = self.client.post(
            self.url, data={"pk": [self.onboarding_task1.pk], "confirm": True, "_confirm": True}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(OnboardingTask.objects.count(), 1)


class OnboardingTaskFeedBulkImportViewTestCase(TestCase):
    """Test the OnboardingTaskFeedBulkImportView view."""

    def setUp(self):
        """Create a superuser and baseline data for testing."""
        self.user = User.objects.create(username="testuser")
        self.client = Client()
        self.client.force_login(self.user)

        self.url = reverse("plugins:netbox_onboarding:onboarding_task_import")

        self.site1 = Site.objects.create(name="USWEST", slug="uswest")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_get_anonymous(self):
        """Verify that the import view cannot be seen by an anonymous user even if permissions are exempted."""
        self.client.logout()
        response = self.client.get(self.url)
        # Redirected to the login page
        self.assertEqual(response.status_code, 302)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_get(self):
        """Verify that the import view can be seen by a user with appropriate permissions."""
        # Attempt to access without permissions
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

        # Add permission
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="netbox_onboarding", codename="add_onboardingtask")
        )

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "utilities/obj_bulk_import.html")

    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_post(self):
        """Verify that tasks can be bulk-imported."""
        csv_data = [
            "site,ip_address",
            "uswest,10.10.10.10",
            "uswest,10.10.10.20",
            "uswest,10.10.10.30",
        ]

        # Attempt to access without permissions
        response = self.client.post(self.url, data={"csv": "\n".join(csv_data)})
        self.assertEqual(response.status_code, 403)

        # Add permission
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="netbox_onboarding", codename="add_onboardingtask")
        )

        response = self.client.post(self.url, data={"csv": "\n".join(csv_data)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(OnboardingTask.objects.count(), len(csv_data) - 1)
