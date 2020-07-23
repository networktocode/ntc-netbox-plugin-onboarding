"""Unit tests for netbox_onboarding.naplam_addons.ios module and its classes.

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
# pylint disable=protected-access
# Python First Party Imports
import os

# Python Third Party Imports
from django.test import TestCase
from napalm import get_network_driver

# NetBox Imports
from dcim.models import Platform

# Application Imports
from netbox_onboarding.onboard import NetdevKeeper, OnboardException

# Onboard class as the name of the platformExtension to allow for the onboarding of several platforms
from netbox_onboarding.onboarding_extensions.ios import OnboardingDriverExtensions as IosExtension

# Load utilities
from .utilities import load_test_output


class IosExtensionTestCase(TestCase):
    """Test the IOS NapalmDeviceExtensions."""

    def test_parse_output(self):
        """Method to test parsing of output through NTC Templates parser"""
        test_output_dir = os.path.join(os.path.dirname(__file__), "fixtures")
        # Verify that the text loading function is working
        expected_text = """Testing of a load config
with line break"""
        test_output = load_test_output(f"{test_output_dir}/00_test_data.txt")
        self.assertEqual(test_output, expected_text)
        self.maxDiff = None

        #
        # Verify Cisco IOS show version
        #

        # Create Mock NAPALM Device
        driver = get_network_driver("mock")
        napalm_device = driver(
            hostname="192.0.2.1", username="user", password=None, optional_args={"path": f"{test_output_dir}"}
        )
        napalm_device.open()

        # Test Single Unit IOS Switch
        textfsm_expected = [
            {
                "position": 1,
                "model": "WS-C3750G-48PS",
                "serial_number": "FOC0948Y2RB",
                "mac_address": "00:16:47:10:AF:00",
            }
        ]

        # Assign mock output to the class for standalone device
        ios_single_device = IosExtension(napalm_device)
        ios_single_device.show_version = load_test_output(f"{test_output_dir}/01_cisco_ios_show_version.txt")
        ios_single_device._parse_with_textfsm()
        self.assertEqual(ios_single_device.driver_addon_result["device_list"], textfsm_expected)

        # Test 4 Unit Stack
        textfsm_expected = [
            {
                "position": 1,
                "mac_address": "f8:7b:20:11:aa:80",
                "serial_number": "FOC11111111",
                "model": "WS-C3850-48U",
            },
            {
                "position": 2,
                "mac_address": "f8:7b:20:22:bb:80",
                "serial_number": "FCW22222222",
                "model": "WS-C3850-48U",
            },
            {
                "position": 3,
                "mac_address": "f8:b7:e2:33:cc:00",
                "serial_number": "FCW33333333",
                "model": "WS-C3850-48U",
            },
            {
                "position": 4,
                "mac_address": "f8:b7:e2:44:dd:00",
                "serial_number": "FCW44444444",
                "model": "WS-C3850-48U",
            },
        ]

        # Assign mock output to the class for standalone device
        ios_quad_stack = IosExtension(napalm_device)
        ios_quad_stack.show_version = load_test_output(f"{test_output_dir}/02_cisco_ios_show_version.txt")
        ios_quad_stack._parse_with_textfsm()
        self.assertEqual(ios_quad_stack.driver_addon_result["device_list"], textfsm_expected)

        # Test IOS Router, expecting the length to be an empty dictionary
        textfsm_expected_router = []

        # Assign the output
        ios_router = IosExtension(napalm_device)
        ios_router.show_version = load_test_output(f"{test_output_dir}/03_cisco_ios_show_version.txt")
        ios_router._parse_with_textfsm()
        self.assertEqual(ios_router.driver_addon_result["device_list"], textfsm_expected_router)
