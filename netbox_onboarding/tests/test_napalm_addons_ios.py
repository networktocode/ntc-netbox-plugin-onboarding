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
from netbox_onboarding.napalm_addons.ios import NapalmDeviceExtensions as IosExtension

# Load utilities
from .utilities import load_test_output


class IosExtensionTestCase(TestCase):
    """Test the IOS NapalmDeviceExtensions."""

    def test_parse_output(self):
        """Method to test parsing of output through pyATS Genie parser"""
        test_output_dir = "/source/netbox_onboarding/tests/fixtures"
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
            hostname="192.0.2.1", username="user", password="password", optional_args={"path": f"{test_output_dir}"}
        )
        napalm_device.open()

        # Test Single Unit IOS Switch
        ios_single_device = IosExtension(napalm_device)
        expected = {
            "1": {
                "active": True,
                "clei_code_num": "CNMWM00ARB",
                "hb_rev_num": "0x05",
                "mac_address": "00:16:47:10:AF:00",
                "mb_assembly_num": "73-9365-08",
                "mb_rev_num": "A0",
                "mb_sn": "FOC09480D0A",
                "model": "WS-C3750G-48PS",
                "model_num": "WS-C3750G-48PS-E",
                "model_rev_num": "C0",
                "ports": "52",
                "power_supply_part_nr": "341-0108-02",
                "power_supply_sn": "DCA09431730",
                "sw_image": "C3750-IPSERVICESK9-M",
                "sw_ver": "15.0(2)SE11",
                "system_sn": "FOC0948Y2RB",
                "top_assembly_part_num": "800-26344-02",
                "top_assembly_rev_num": "B0",
                "version_id": "V02",
            }
        }

        # Assign mock output to the class for standalone device
        ios_single_device.show_version = load_test_output(f"{test_output_dir}/01_cisco_ios_show_version.txt")
        result = ios_single_device.parse_stack_commands()
        self.assertEqual(result, expected)

        # Test 4 Unit Stack
        ios_quad_stack = IosExtension(napalm_device)
        expected = {
            "1": {
                "active": True,
                "mac_address": "f8:7b:20:11:aa:80",
                "mb_assembly_num": "73-15799-08",
                "mb_rev_num": "A0",
                "mb_sn": "FOC11122222",
                "mode": "INSTALL",
                "model": "WS-C3850-48U",
                "model_num": "WS-C3850-48U",
                "model_rev_num": "AB0",
                "ports": "56",
                "sw_image": "cat3k_caa-universalk9",
                "sw_ver": "03.06.05E",
                "system_sn": "FOC11111111",
                "uptime": "28 weeks, 1 day, 8 hours, 0 minutes",
            },
            "2": {
                "active": False,
                "mac_address": "f8:7b:20:22:bb:80",
                "mb_assembly_num": "73-15799-08",
                "mb_rev_num": "A0",
                "mb_sn": "FOC22222222",
                "mode": "INSTALL",
                "model": "WS-C3850-48U",
                "model_num": "WS-C3850-48U",
                "model_rev_num": "AB0",
                "ports": "56",
                "sw_image": "cat3k_caa-universalk9",
                "sw_ver": "03.06.05E",
                "system_sn": "FCW22222222",
                "uptime": "28 weeks, 1 day, 8 hours, 1 minute",
            },
            "3": {
                "active": False,
                "mac_address": "f8:b7:e2:33:cc:00",
                "mb_assembly_num": "73-15799-08",
                "mb_rev_num": "A0",
                "mb_sn": "FOC33333333",
                "mode": "INSTALL",
                "model": "WS-C3850-48U",
                "model_num": "WS-C3850-48U",
                "model_rev_num": "AB0",
                "ports": "56",
                "sw_image": "cat3k_caa-universalk9",
                "sw_ver": "03.06.05E",
                "system_sn": "FCW33333333",
                "uptime": "28 weeks, 1 day, 8 hours, 0 minutes",
            },
            "4": {
                "active": False,
                "mac_address": "f8:b7:e2:44:dd:00",
                "mb_assembly_num": "73-15799-08",
                "mb_rev_num": "A0",
                "mb_sn": "FOC44444444",
                "mode": "INSTALL",
                "model": "WS-C3850-48U",
                "model_num": "WS-C3850-48U",
                "model_rev_num": "AB0",
                "ports": "56",
                "sw_image": "cat3k_caa-universalk9",
                "sw_ver": "03.06.05E",
                "system_sn": "FCW44444444",
                "uptime": "28 weeks, 1 day, 8 hours, 0 minutes",
            },
        }

        # Assign mock output to the class for standalone device
        ios_quad_stack.show_version = load_test_output(f"{test_output_dir}/02_cisco_ios_show_version.txt")
        result = ios_quad_stack.parse_stack_commands()
        self.assertEqual(result, expected)

        # Test IOS Router, expecting the length to be an empty dictionary
        ios_router = IosExtension(napalm_device)
        expected_router = {}

        # Assign the output
        ios_router.show_version = load_test_output(f"{test_output_dir}/03_cisco_ios_show_version.txt")
        result = ios_router.parse_stack_commands()
        self.assertEqual(result, expected_router)
