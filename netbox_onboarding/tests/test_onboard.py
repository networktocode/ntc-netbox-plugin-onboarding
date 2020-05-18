"""Unit tests for netbox_onboarding.onboard module and its classes.

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

from dcim.models import Site, Device, Interface, Manufacturer, DeviceType, DeviceRole, Platform
from ipam.models import IPAddress

from netbox_onboarding.models import OnboardingTask
from netbox_onboarding.onboard import NetboxKeeper, NetdevKeeper, OnboardException


class NetboxKeeperTestCase(TestCase):
    """Test the NetboxKeeper Class."""

    def setUp(self):
        """Create a superuser and token for API calls."""
        self.site1 = Site.objects.create(name="USWEST", slug="uswest")

        self.manufacturer1 = Manufacturer.objects.create(name="Juniper", slug="juniper")
        self.platform1 = Platform.objects.create(name="JunOS", slug="junos")
        self.device_type1 = DeviceType.objects.create(slug="srx3600", model="SRX3600", manufacturer=self.manufacturer1)
        self.device_role1 = DeviceRole.objects.create(name="Firewall", slug="firewall")

        self.onboarding_task1 = OnboardingTask.objects.create(ip_address="10.10.10.10", site=self.site1)
        self.onboarding_task2 = OnboardingTask.objects.create(
            ip_address="192.168.1.1", site=self.site1, role=self.device_role1
        )
        self.onboarding_task3 = OnboardingTask.objects.create(
            ip_address="192.168.1.2", site=self.site1, role=self.device_role1, platform=self.platform1
        )

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

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_type(create_manufacturer=False, create_device_type=False)
            self.assertEqual(exc_info.exception.message, "ERROR manufacturer not found: cisco")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_type(create_manufacturer=True, create_device_type=False)
            self.assertEqual(exc_info.exception.message, "ERROR device type not found: csr1000v")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        nbk.ensure_device_type(create_manufacturer=True, create_device_type=True)
        self.assertIsInstance(nbk.manufacturer, Manufacturer)
        self.assertIsInstance(nbk.device_type, DeviceType)

    def test_ensure_device_type_present(self):
        """Verify ensure_device_type function when Manufacturer and DeviceType object are already present."""
        nbk = NetboxKeeper(self.ndk2)

        nbk.ensure_device_type(create_manufacturer=False, create_device_type=False)
        self.assertEqual(nbk.manufacturer, self.manufacturer1)
        self.assertEqual(nbk.device_type, self.device_type1)

    def test_ensure_device_role_not_exist(self):
        """Verify ensure_device_role function when DeviceRole do not already exist."""
        nbk = NetboxKeeper(self.ndk1)

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_role(create_device_role=False, default_device_role="mytestrole")
            self.assertEqual(exc_info.exception.message, "ERROR device role not found: mytestrole")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        nbk.ensure_device_role(create_device_role=True, default_device_role="mytestrole")
        self.assertIsInstance(nbk.netdev.ot.role, DeviceRole)
        self.assertEqual(nbk.netdev.ot.role.slug, "mytestrole")

    def test_ensure_device_role_exist(self):
        """Verify ensure_device_role function when DeviceRole exist but is not assigned to the OT."""
        nbk = NetboxKeeper(self.ndk1)

        nbk.ensure_device_role(create_device_role=True, default_device_role="firewall")
        self.assertEqual(nbk.netdev.ot.role, self.device_role1)

    def test_ensure_device_role_assigned(self):
        """Verify ensure_device_role function when DeviceRole exist and is already assigned."""
        nbk = NetboxKeeper(self.ndk2)

        nbk.ensure_device_role(create_device_role=True, default_device_role="firewall")
        self.assertEqual(nbk.netdev.ot.role, self.device_role1)

    def test_ensure_device_instance_not_exist(self):
        """Verify ensure_device_instance function."""
        nbk = NetboxKeeper(self.ndk2)
        nbk.device_type = self.device_type1
        nbk.netdev.ot = self.onboarding_task3

        nbk.ensure_device_instance()
        self.assertIsInstance(nbk.device, Device)
        self.assertEqual(nbk.device, nbk.netdev.ot.created_device)
        self.assertEqual(nbk.device.serial, "123456")

    def test_ensure_interface_not_exist(self):
        """Verify ensure_interface function when the interface do not exist."""
        nbk = NetboxKeeper(self.ndk2)
        nbk.device_type = self.device_type1
        nbk.netdev.ot = self.onboarding_task3

        nbk.ensure_device_instance()

        nbk.ensure_interface()
        self.assertIsInstance(nbk.interface, Interface)
        self.assertEqual(nbk.interface.name, "ge-0/0/0")

    def test_ensure_interface_exist(self):
        """Verify ensure_interface function when the interface already exist."""
        nbk = NetboxKeeper(self.ndk2)
        nbk.device_type = self.device_type1
        nbk.netdev.ot = self.onboarding_task3

        nbk.ensure_device_instance()
        intf = Interface.objects.create(name=nbk.netdev.mgmt_ifname, device=nbk.device)

        nbk.ensure_interface()
        self.assertEqual(nbk.interface, intf)

    def test_ensure_primary_ip_not_exist(self):
        """Verify ensure_primary_ip function when the Ip address do not already exist."""
        nbk = NetboxKeeper(self.ndk2)
        nbk.device_type = self.device_type1
        nbk.netdev.ot = self.onboarding_task3

        nbk.ensure_device_instance()
        nbk.ensure_interface()
        nbk.ensure_primary_ip()
        self.assertIsInstance(nbk.primary_ip, IPAddress)
        self.assertEqual(nbk.primary_ip.interface, nbk.interface)
