"""Django urlpatterns declaration for netbox_onboarding plugin.

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
from django.urls import path
from extras.views import ObjectChangeLogView

from .models import OnboardingTask
from .views import (
    OnboardingTaskView,
    OnboardingTaskListView,
    OnboardingTaskCreateView,
    OnboardingTaskBulkDeleteView,
    OnboardingTaskFeedBulkImportView,
)

urlpatterns = [
    path("", OnboardingTaskListView.as_view(), name="onboardingtask_list"),
    path("<int:pk>/", OnboardingTaskView.as_view(), name="onboardingtask"),
    path("add/", OnboardingTaskCreateView.as_view(), name="onboardingtask_add"),
    path("delete/", OnboardingTaskBulkDeleteView.as_view(), name="onboardingtask_bulk_delete"),
    path("import/", OnboardingTaskFeedBulkImportView.as_view(), name="onboardingtask_import"),
    path(
        "<int:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="onboardingtask_changelog",
        kwargs={"model": OnboardingTask},
    ),
]
