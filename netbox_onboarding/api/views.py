"""Django REST Framework API views for device onboarding.

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

# from drf_yasg.openapi import Parameter, TYPE_STRING
# from drf_yasg.utils import swagger_auto_schema

from rest_framework import mixins, viewsets

# from rest_framework.decorators import action
# from rest_framework.response import Response

# from utilities.api import IsAuthenticatedOrLoginNotRequired

# from dcim.models import Device, Site, Platform, DeviceRole

from netbox_onboarding.models import OnboardingTask
from netbox_onboarding.filters import OnboardingTaskFilter

# from netbox_onboarding.choices import OnboardingStatusChoices
from .serializers import OnboardingTaskSerializer


class OnboardingTaskView(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Create, check status of, and delete onboarding tasks.

    In-place updates (PUT, PATCH) of tasks are not permitted.
    """

    queryset = OnboardingTask.objects.all()
    filterset_class = OnboardingTaskFilter
    serializer_class = OnboardingTaskSerializer
