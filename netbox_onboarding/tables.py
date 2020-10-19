"""Tables for device onboarding tasks.

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
import django_tables2 as tables
from utilities.tables import BaseTable, ToggleColumn
from .models import OnboardingTask


class OnboardingTaskTable(BaseTable):
    """Table for displaying OnboardingTask instances."""

    pk = ToggleColumn()
    id = tables.LinkColumn()
    site = tables.LinkColumn()
    platform = tables.LinkColumn()
    created_device = tables.LinkColumn()

    class Meta(BaseTable.Meta):  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = (
            "pk",
            "id",
            "created",
            "ip_address",
            "site",
            "platform",
            "created_device",
            "status",
            "failed_reason",
            "message",
        )


class OnboardingTaskFeedBulkTable(BaseTable):
    """TODO document me."""

    site = tables.LinkColumn()

    class Meta(BaseTable.Meta):  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = (
            "id",
            "created",
            "site",
            "platform",
            "ip_address",
            "port",
            "timeout",
        )
