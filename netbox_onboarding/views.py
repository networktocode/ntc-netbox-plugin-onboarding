"""Django views for device onboarding.

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
import logging
from django.contrib.auth.mixins import PermissionRequiredMixin
from utilities.views import BulkDeleteView, BulkImportView, ObjectEditView, ObjectListView

from .filters import OnboardingTaskFilter
from .forms import OnboardingTaskForm, OnboardingTaskFilterForm, OnboardingTaskFeedCSVForm
from .models import OnboardingTask
from .tables import OnboardingTaskTable, OnboardingTaskFeedBulkTable

log = logging.getLogger("rq.worker")
log.setLevel(logging.DEBUG)


class OnboardingTaskListView(PermissionRequiredMixin, ObjectListView):
    """View for listing all extant OnboardingTasks."""

    permission_required = "netbox_onboarding.view_onboardingtask"
    queryset = OnboardingTask.objects.all().order_by("-id")
    filterset = OnboardingTaskFilter
    filterset_form = OnboardingTaskFilterForm
    table = OnboardingTaskTable
    template_name = "netbox_onboarding/onboarding_tasks_list.html"


class OnboardingTaskCreateView(PermissionRequiredMixin, ObjectEditView):
    """View for creating a new OnboardingTask."""

    permission_required = "netbox_onboarding.add_onboardingtask"
    model = OnboardingTask
    queryset = OnboardingTask.objects.all()
    model_form = OnboardingTaskForm
    template_name = "netbox_onboarding/onboarding_task_edit.html"
    default_return_url = "plugins:netbox_onboarding:onboarding_task_list"


class OnboardingTaskBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    """View for deleting one or more OnboardingTasks."""

    permission_required = "netbox_onboarding.delete_onboardingtask"
    queryset = OnboardingTask.objects.filter()  # TODO: can we exclude currently-running tasks?
    table = OnboardingTaskTable
    default_return_url = "plugins:netbox_onboarding:onboarding_task_list"


class OnboardingTaskFeedBulkImportView(PermissionRequiredMixin, BulkImportView):
    """View for bulk-importing a CSV file to create OnboardingTasks."""

    permission_required = "netbox_onboarding.add_onboardingtask"
    model_form = OnboardingTaskFeedCSVForm
    table = OnboardingTaskFeedBulkTable
    default_return_url = "plugins:netbox_onboarding:onboarding_task_list"
