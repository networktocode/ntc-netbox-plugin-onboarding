"""Unit tests for netbox_onboarding REST API.

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
from django.test import TestCase

from dcim.models import Site, Manufacturer, DeviceType

from netbox_onboarding.models import OnboardingTask
from netbox_onboarding.onboard import NetboxKeeper, NetdevKeeper, OnboardException


class NetboxKeeperTestCase(TestCase):
    """Test the NetboxKeeper Class."""

    def setUp(self):
        """Create a superuser and token for API calls."""
        self.site1 = Site.objects.create(name="USWEST", slug="uswest")

        # self.platform1 = Platform.objects.create(name="NXOS", slug="nxos")

        self.manufacturer1 = Manufacturer.objects.create(name="juniper", slug="juniper")
        self.device_type1 = DeviceType.objects.create(slug="srx3600", model="SRX3600", manufacturer=self.manufacturer1)

        self.onboarding_task1 = OnboardingTask.objects.create(ip_address="10.10.10.10", site=self.site1)
        self.onboarding_task2 = OnboardingTask.objects.create(ip_address="192.168.1.1", site=self.site1)

        self.ndk1 = NetdevKeeper(self.onboarding_task1)
        self.ndk1.hostname = "device1"
        self.ndk1.vendor = "cisco"
        self.ndk1.model = "csr1000v"
        self.ndk1.serial_number = "123456"
        self.ndk1.mgmt_ifname = "GigaEthernet0"
        self.ndk1.mgmt_pflen = 24

        self.ndk2 = NetdevKeeper(self.onboarding_task2)
        self.ndk2.hostname = "device2"
        self.ndk2.vendor = "juniper"
        self.ndk2.model = "srx3600"
        self.ndk2.serial_number = "123456"
        self.ndk2.mgmt_ifname = "ge-0/0/0"
        self.ndk2.mgmt_pflen = 24

    def test_ensure_device_type_missing(self):
        """Verify ensure_device_type function when Manufacturer and DeviceType object are not present."""
        nbk = NetboxKeeper(self.ndk1)

        ## Find how to assert better which exception is catched
        with self.assertRaises(OnboardException):
            nbk.ensure_device_type(create_manufacturer=False, create_device_type=False)

        nbk.ensure_device_type(create_manufacturer=True, create_device_type=True)
        self.assertEqual(isinstance(nbk.manufacturer, Manufacturer), True)
        self.assertEqual(isinstance(nbk.device_type, DeviceType), True)

    def test_ensure_device_type_present(self):
        """Verify ensure_device_type function when Manufacturer and DeviceType object are already present."""
        nbk = NetboxKeeper(self.ndk2)

        nbk.ensure_device_type(create_manufacturer=False, create_device_type=False)
        self.assertEqual(nbk.manufacturer, self.manufacturer1)
        self.assertEqual(nbk.device_type, self.device_type1)
