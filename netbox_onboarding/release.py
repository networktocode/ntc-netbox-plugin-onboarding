"""Release variables of the NetBox.

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

from packaging import version
from django.conf import settings

NETBOX_RELEASE_CURRENT = version.parse(settings.VERSION)
NETBOX_RELEASE_28 = version.parse("2.8")
NETBOX_RELEASE_29 = version.parse("2.9")
NETBOX_RELEASE_210 = version.parse("2.10")
NETBOX_RELEASE_211 = version.parse("2.11")
