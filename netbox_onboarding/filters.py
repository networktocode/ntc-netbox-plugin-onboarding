"""Filtering logic for OnboardingTask instances.

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

import django_filters
from django.db.models import Q

from dcim.models import Site, DeviceRole, Platform

from .release import NETBOX_RELEASE_CURRENT, NETBOX_RELEASE_211
from .models import OnboardingTask


if NETBOX_RELEASE_CURRENT < NETBOX_RELEASE_211:
    from utilities.filters import NameSlugSearchFilterSet  # pylint: disable=no-name-in-module, import-error

    class FitersetMixin(NameSlugSearchFilterSet):
        """FilterSet Mixin."""


else:
    from netbox.filtersets import BaseFilterSet  # pylint: disable=no-name-in-module, import-error

    class FitersetMixin(BaseFilterSet):
        """FilterSet Mixin."""


class OnboardingTaskFilter(FitersetMixin):
    """Filter capabilities for OnboardingTask instances."""

    q = django_filters.CharFilter(method="search", label="Search",)

    site = django_filters.ModelMultipleChoiceFilter(
        field_name="site__slug", queryset=Site.objects.all(), to_field_name="slug", label="Site (slug)",
    )

    site_id = django_filters.ModelMultipleChoiceFilter(queryset=Site.objects.all(), label="Site (ID)",)

    platform = django_filters.ModelMultipleChoiceFilter(
        field_name="platform__slug", queryset=Platform.objects.all(), to_field_name="slug", label="Platform (slug)",
    )

    role = django_filters.ModelMultipleChoiceFilter(
        field_name="role__slug", queryset=DeviceRole.objects.all(), to_field_name="slug", label="Device Role (slug)",
    )

    class Meta:  # noqa: D106 "Missing docstring in public nested class"
        model = OnboardingTask
        fields = ["id", "site", "site_id", "platform", "role", "status", "failed_reason"]

    def search(self, queryset, name, value):  # pylint: disable=unused-argument, no-self-use
        """Perform the filtered search."""
        if not value.strip():
            return queryset
        qs_filter = (
            Q(id__icontains=value)
            | Q(ip_address__icontains=value)
            | Q(site__name__icontains=value)
            | Q(platform__name__icontains=value)
            | Q(created_device__name__icontains=value)
            | Q(status__icontains=value)
            | Q(failed_reason__icontains=value)
            | Q(message__icontains=value)
        )
        return queryset.filter(qs_filter)
