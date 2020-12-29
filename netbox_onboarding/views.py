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

from django.shortcuts import get_object_or_404, render


from .release import NETBOX_RELEASE_CURRENT, NETBOX_RELEASE_29, NETBOX_RELEASE_210
from .filters import OnboardingTaskFilter
from .forms import OnboardingTaskForm, OnboardingTaskFilterForm, OnboardingTaskFeedCSVForm
from .models import OnboardingTask
from .tables import OnboardingTaskTable, OnboardingTaskFeedBulkTable

logger = logging.getLogger("rq.worker")

# pylint: disable=ungrouped-imports,no-name-in-module

if NETBOX_RELEASE_CURRENT < NETBOX_RELEASE_29:
    from django.contrib.auth.mixins import PermissionRequiredMixin
    from django.views.generic import View
    from utilities.views import BulkDeleteView, BulkImportView, ObjectEditView, ObjectListView

    class ReleaseMixinOnboardingTaskView(PermissionRequiredMixin, View):
        """Release Mixin View for presenting a single OnboardingTask."""

        permission_required = "netbox_onboarding.view_onboardingtask"

    class ReleaseMixinOnboardingTaskListView(PermissionRequiredMixin, ObjectListView):
        """Release Mixin View for listing all extant OnboardingTasks."""

        permission_required = "netbox_onboarding.view_onboardingtask"

    class ReleaseMixinOnboardingTaskCreateView(PermissionRequiredMixin, ObjectEditView):
        """Release Mixin View for creating a new OnboardingTask."""

        permission_required = "netbox_onboarding.add_onboardingtask"

    class ReleaseMixinOnboardingTaskBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
        """Release Mixin View for deleting one or more OnboardingTasks."""

        permission_required = "netbox_onboarding.delete_onboardingtask"

    class ReleaseMixinOnboardingTaskFeedBulkImportView(PermissionRequiredMixin, BulkImportView):
        """Release Mixin View for bulk-importing a CSV file to create OnboardingTasks."""

        permission_required = "netbox_onboarding.add_onboardingtask"


elif NETBOX_RELEASE_29 <= NETBOX_RELEASE_CURRENT < NETBOX_RELEASE_210:
    from utilities.views import ObjectView, BulkDeleteView, BulkImportView, ObjectEditView, ObjectListView

    class ReleaseMixinOnboardingTaskView(ObjectView):
        """Release Mixin View for presenting a single OnboardingTask."""

    class ReleaseMixinOnboardingTaskListView(ObjectListView):
        """Release Mixin View for listing all extant OnboardingTasks."""

    class ReleaseMixinOnboardingTaskCreateView(ObjectEditView):
        """Release Mixin View for creating a new OnboardingTask."""

    class ReleaseMixinOnboardingTaskBulkDeleteView(BulkDeleteView):
        """Release Mixin View for deleting one or more OnboardingTasks."""

    class ReleaseMixinOnboardingTaskFeedBulkImportView(BulkImportView):
        """Release Mixin View for bulk-importing a CSV file to create OnboardingTasks."""


elif NETBOX_RELEASE_CURRENT >= NETBOX_RELEASE_210:
    from netbox.views import generic

    # ObjectView, BulkDeleteView, BulkImportView, ObjectEditView, ObjectListView

    class ReleaseMixinOnboardingTaskView(generic.ObjectView):
        """Release Mixin View for presenting a single OnboardingTask."""

    class ReleaseMixinOnboardingTaskListView(generic.ObjectListView):
        """Release Mixin View for listing all extant OnboardingTasks."""

    class ReleaseMixinOnboardingTaskCreateView(generic.ObjectEditView):
        """Release Mixin View for creating a new OnboardingTask."""

    class ReleaseMixinOnboardingTaskBulkDeleteView(generic.BulkDeleteView):
        """Release Mixin View for deleting one or more OnboardingTasks."""

    class ReleaseMixinOnboardingTaskFeedBulkImportView(generic.BulkImportView):
        """Release Mixin View for bulk-importing a CSV file to create OnboardingTasks."""


class OnboardingTaskView(ReleaseMixinOnboardingTaskView):
    """View for presenting a single OnboardingTask."""

    queryset = OnboardingTask.objects.all()

    def get(self, request, pk):  # pylint: disable=invalid-name, missing-function-docstring
        """Get request."""
        instance = get_object_or_404(self.queryset, pk=pk)

        return render(
            request, "netbox_onboarding/onboardingtask.html", {"object": instance, "onboardingtask": instance}
        )


class OnboardingTaskListView(ReleaseMixinOnboardingTaskListView):
    """View for listing all extant OnboardingTasks."""

    queryset = OnboardingTask.objects.all().order_by("-id")
    filterset = OnboardingTaskFilter
    filterset_form = OnboardingTaskFilterForm
    table = OnboardingTaskTable
    template_name = "netbox_onboarding/onboarding_tasks_list.html"


class OnboardingTaskCreateView(ReleaseMixinOnboardingTaskCreateView):
    """View for creating a new OnboardingTask."""

    model = OnboardingTask
    queryset = OnboardingTask.objects.all()
    model_form = OnboardingTaskForm
    template_name = "netbox_onboarding/onboarding_task_edit.html"
    default_return_url = "plugins:netbox_onboarding:onboardingtask_list"


class OnboardingTaskBulkDeleteView(ReleaseMixinOnboardingTaskBulkDeleteView):
    """View for deleting one or more OnboardingTasks."""

    queryset = OnboardingTask.objects.filter()  # TODO: can we exclude currently-running tasks?
    table = OnboardingTaskTable
    default_return_url = "plugins:netbox_onboarding:onboardingtask_list"


class OnboardingTaskFeedBulkImportView(ReleaseMixinOnboardingTaskFeedBulkImportView):
    """View for bulk-importing a CSV file to create OnboardingTasks."""

    queryset = OnboardingTask.objects.all()
    model_form = OnboardingTaskFeedCSVForm
    table = OnboardingTaskFeedBulkTable
    default_return_url = "plugins:netbox_onboarding:onboardingtask_list"
