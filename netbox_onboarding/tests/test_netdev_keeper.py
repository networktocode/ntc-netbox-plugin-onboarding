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

from dcim.models import Platform
from netbox_onboarding.onboard import NetdevKeeper, OnboardException


class NetdevKeeperTestCase(TestCase):
    """Test the NetdevKeeper Class."""

    def setUp(self):
        """Create a superuser and token for API calls."""
        self.platform1 = Platform.objects.create(name="JunOS", slug="junos", napalm_driver="junos")
        self.platform2 = Platform.objects.create(name="Cisco NX-OS", slug="cisco-nx-os")

    def test_get_platform_object_from_netbox(self):
        """Test of platform object from netbox."""
        # Test assigning platform
        platform = NetdevKeeper.get_platform_object_from_netbox("junos", create_platform_if_missing=False)
        self.assertIsInstance(platform, Platform)

        # Test creation of missing platform object
        platform = NetdevKeeper.get_platform_object_from_netbox("arista_eos", create_platform_if_missing=True)
        self.assertIsInstance(platform, Platform)
        self.assertEqual(platform.napalm_driver, "eos")

        # Test failed unable to find the device and not part of the NETMIKO TO NAPALM keys
        with self.assertRaises(OnboardException) as exc_info:
            platform = NetdevKeeper.get_platform_object_from_netbox("notthere", create_platform_if_missing=True)
            self.assertEqual(
                exc_info.exception.message,
                "ERROR platform not found in NetBox and it's eligible for auto-creation: notthere",
            )
            self.assertEqual(exc_info.exception.reason, "fail-general")

        # Test searching for an object, does not exist, but create_platform is false
        with self.assertRaises(OnboardException) as exc_info:
            platform = NetdevKeeper.get_platform_object_from_netbox("cisco_ios", create_platform_if_missing=False)
            self.assertEqual(exc_info.exception.message, "ERROR platform not found in NetBox: cisco_ios")
            self.assertEqual(exc_info.exception.reason, "fail-general")

        # Test NAPALM Driver not defined in NetBox
        with self.assertRaises(OnboardException) as exc_info:
            platform = NetdevKeeper.get_platform_object_from_netbox("cisco-nx-os", create_platform_if_missing=False)
            self.assertEqual(exc_info.exception.message, "ERROR platform is missing the NAPALM Driver: cisco-nx-os")
            self.assertEqual(exc_info.exception.reason, "fail-general")
