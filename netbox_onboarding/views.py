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
from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import render
from django_rq import get_queue
from utilities.views import BulkImportView, ObjectListView

from netbox_onboarding.utils.credentials import Credentials
from .filters import OnboardingTaskFilter
from .forms import OnboardingTaskFilterForm, OnboardingTaskFeedCSVForm
from .models import OnboardingTask
from .tables import OnboardingTaskTable, OnboardingTaskFeedBulkTable

log = logging.getLogger("rq.worker")
log.setLevel(logging.DEBUG)


class OnboardingTaskListView(PermissionRequiredMixin, ObjectListView):
    """View for listing all extant OnboardingTasks."""

    permission_required = "dcim.view_device"
    queryset = OnboardingTask.objects.all().order_by("-id")
    filterset = OnboardingTaskFilter
    filterset_form = OnboardingTaskFilterForm
    table = OnboardingTaskTable
    template_name = "netbox_onboarding/onboarding_tasks_list.html"


class OnboardingTaskFeedBulkImportView(PermissionRequiredMixin, BulkImportView):
    """View for bulk-importing a CSV file to create OnboardingTasks."""

    permission_required = "dcim.add_device"
    model_form = OnboardingTaskFeedCSVForm
    table = OnboardingTaskFeedBulkTable
    default_return_url = "plugins:netbox_onboarding:onboarding_task_list"

    def post(self, request):
        """Process an HTTP POST request."""
        new_objs = []
        form = self._import_form(request.POST)

        if form.is_valid():
            try:
                # Iterate through CSV data and bind each row to a new model form instance.
                with transaction.atomic():
                    headers, records = form.cleaned_data["csv"]
                    for row, data in enumerate(records, start=1):
                        obj_form = self.model_form(data, headers=headers)
                        if obj_form.is_valid():
                            obj = self._save_obj(obj_form, request)
                            new_objs.append(obj)
                        else:
                            for field, err in obj_form.errors.items():
                                form.add_error("csv", "Row {} {}: {}".format(row, field, err[0]))
                            raise ValidationError("")

                for ot in new_objs:
                    credentials = Credentials(username=ot.username, password=ot.password, secret=ot.secret,)

                    ot.username = ""
                    ot.password = ""
                    ot.secret = ""
                    ot.owner = self.request.user
                    ot.save()

                    get_queue("default").enqueue("netbox_onboarding.worker.onboard_device", ot.pk, credentials)

                if new_objs:
                    msg = "Imported {} {}".format(len(new_objs), new_objs[0]._meta.verbose_name_plural)
                    messages.success(request, msg)

                    return render(
                        request,
                        "import_success.html",
                        {"table": self.table(new_objs), "return_url": self.get_return_url(request),},
                    )

            except ValidationError:
                pass

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "fields": self.model_form().fields,
                "obj_type": self.model_form._meta.model._meta.verbose_name,  # pylint:disable=no-member
                "return_url": self.get_return_url(request),
            },
        )
