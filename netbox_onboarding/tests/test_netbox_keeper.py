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
from socket import gaierror
from unittest import mock
from django.test import TestCase
from django.utils.text import slugify

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
        self.platform2 = Platform.objects.create(name="Cisco NX-OS", slug="cisco-nx-os")
        self.device_type1 = DeviceType.objects.create(slug="srx3600", model="SRX3600", manufacturer=self.manufacturer1)
        self.device_role1 = DeviceRole.objects.create(name="Firewall", slug="firewall")

        self.onboarding_task1 = OnboardingTask.objects.create(ip_address="10.10.10.10", site=self.site1)
        self.onboarding_task2 = OnboardingTask.objects.create(
            ip_address="192.168.1.1", site=self.site1, role=self.device_role1
        )
        self.onboarding_task3 = OnboardingTask.objects.create(
            ip_address="192.168.1.2", site=self.site1, role=self.device_role1, platform=self.platform1
        )
        self.onboarding_task4 = OnboardingTask.objects.create(
            ip_address="ntc123.local", site=self.site1, role=self.device_role1, platform=self.platform1
        )
        self.onboarding_task5 = OnboardingTask.objects.create(
            ip_address="bad.local", site=self.site1, role=self.device_role1, platform=self.platform1
        )
        self.onboarding_task6 = OnboardingTask.objects.create(
            ip_address="192.0.2.2", site=self.site1, role=self.device_role1, platform=self.platform2
        )
        self.onboarding_task7 = OnboardingTask.objects.create(
            ip_address="192.0.2.1/32", site=self.site1, role=self.device_role1, platform=self.platform1
        )

        self.ndk1 = NetdevKeeper(self.onboarding_task1)
        self.ndk1.hostname = "device1"
        self.ndk1.vendor = "Cisco"
        self.ndk1.model = "CSR1000v"
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
            self.assertEqual(exc_info.exception.message, "ERROR manufacturer not found: Cisco")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_type(create_manufacturer=True, create_device_type=False)
            self.assertEqual(exc_info.exception.message, "ERROR device type not found: CSR1000v")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        nbk.ensure_device_type(create_manufacturer=True, create_device_type=True)
        self.assertIsInstance(nbk.manufacturer, Manufacturer)
        self.assertIsInstance(nbk.device_type, DeviceType)
        self.assertEqual(nbk.manufacturer.slug, slugify(self.ndk1.vendor))
        self.assertEqual(nbk.device_type.slug, slugify(self.ndk1.model))

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

        role = "My-Test-Role"
        nbk.ensure_device_role(create_device_role=True, default_device_role=role)
        self.assertIsInstance(nbk.netdev.ot.role, DeviceRole)
        self.assertEqual(nbk.netdev.ot.role.slug, slugify(role))

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

        nbk.ensure_device_instance(default_status="planned")
        self.assertIsInstance(nbk.device, Device)
        self.assertEqual(nbk.device.status, "planned")
        self.assertEqual(nbk.device.platform, self.platform1)
        self.assertEqual(nbk.device, nbk.netdev.ot.created_device)
        self.assertEqual(nbk.device.serial, "123456")

    def test_ensure_device_instance_exist(self):
        """Verify ensure_device_instance function."""
        device = Device.objects.create(
            name=self.ndk2.hostname,
            site=self.site1,
            device_type=self.device_type1,
            device_role=self.device_role1,
            status="planned",
            serial="987654",
        )

        nbk = NetboxKeeper(self.ndk2)
        nbk.netdev.ot = self.onboarding_task3
        self.assertEqual(nbk.device, None)
        nbk.ensure_device_instance(default_status="active")
        self.assertIsInstance(nbk.device, Device)
        self.assertEqual(nbk.device.status, "planned")
        self.assertEqual(nbk.device.platform, self.platform1)
        self.assertEqual(nbk.device, device)
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
        """Verify ensure_primary_ip function when the IP address do not already exist."""
        nbk = NetboxKeeper(self.ndk2)
        nbk.device_type = self.device_type1
        nbk.netdev.ot = self.onboarding_task3

        nbk.ensure_device_instance()
        nbk.ensure_interface()
        nbk.ensure_primary_ip()
        self.assertIsInstance(nbk.primary_ip, IPAddress)
        self.assertEqual(nbk.primary_ip.interface, nbk.interface)

    @mock.patch("netbox_onboarding.onboard.socket.gethostbyname")
    def test_check_ip(self, mock_get_hostbyname):
        """Check DNS to IP address."""
        # Look up response value
        mock_get_hostbyname.return_value = "192.0.2.1"

        # Create a Device Keeper object of the device
        ndk4 = NetdevKeeper(self.onboarding_task4)

        # Check that the IP address is returned
        self.assertTrue(ndk4.check_ip())

        # Run the check to change the IP address
        self.assertEqual(ndk4.ot.ip_address, "192.0.2.1")

    @mock.patch("netbox_onboarding.onboard.socket.gethostbyname")
    def test_failed_check_ip(self, mock_get_hostbyname):
        """Check DNS to IP address failing."""
        # Look up a failed response
        mock_get_hostbyname.side_effect = gaierror(8)
        ndk5 = NetdevKeeper(self.onboarding_task5)
        ndk7 = NetdevKeeper(self.onboarding_task7)

        # Check for bad.local raising an exception
        with self.assertRaises(OnboardException) as exc_info:
            ndk5.check_ip()
            self.assertEqual(exc_info.exception.message, "ERROR failed to complete DNS lookup: bad.local")
            self.assertEqual(exc_info.exception.reason, "fail-dns")

        # Check for exception with prefix address entered
        with self.assertRaises(OnboardException) as exc_info:
            ndk7.check_ip()
            self.assertEqual(exc_info.exception.reason, "fail-prefix")
            self.assertEqual(exc_info.exception.message, "ERROR appears a prefix was entered: 192.0.2.1/32")

    def test_platform_map(self):
        """Verify platform mapping of netmiko to slug functionality."""
        # Create static mapping
        platform_map = {"cisco_ios": "ios", "arista_eos": "eos", "cisco_nxos": "cisco-nxos"}

        # Generate an instance of a Cisco IOS device with the mapping defined
        self.ndk1 = NetdevKeeper(self.onboarding_task1)

        #
        # Test positive assertions
        #

        # Test Cisco_ios
        self.assertEqual(self.ndk1.check_netmiko_conversion("cisco_ios", platform_map=platform_map), "ios")
        # Test Arista EOS
        self.assertEqual(self.ndk1.check_netmiko_conversion("arista_eos", platform_map=platform_map), "eos")
        # Test cisco_nxos
        self.assertEqual(self.ndk1.check_netmiko_conversion("cisco_nxos", platform_map=platform_map), "cisco-nxos")

        #
        # Test Negative assertion
        #

        # Test a non-converting item
        self.assertEqual(
            self.ndk1.check_netmiko_conversion("cisco-device-platform", platform_map=platform_map),
            "cisco-device-platform",
        )
