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
from django.conf import settings
from django.test import TestCase
from django.utils.text import slugify
from dcim.models import Site, Manufacturer, DeviceType, DeviceRole, Device, Interface, Platform
from ipam.models import IPAddress

# from netbox_onboarding.netbox_keeper import NetdevKeeper
from netbox_onboarding.exceptions import OnboardException
from netbox_onboarding.netbox_keeper import NetboxKeeper

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["netbox_onboarding"]


class NetboxKeeperTestCase(TestCase):
    """Test the NetboxKeeper Class."""

    def setUp(self):
        """Create a superuser and token for API calls."""
        self.site1 = Site.objects.create(name="USWEST", slug="uswest")

    def test_ensure_device_manufacturer_strict_missing(self):
        """Verify ensure_device_manufacturer function when Manufacturer object is not present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "strict"
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_site_slug": self.site1.slug,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_manufacturer(create_manufacturer=False)
            self.assertEqual(exc_info.exception.message, "ERROR manufacturer not found: Cisco")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        nbk.ensure_device_manufacturer(create_manufacturer=True)
        self.assertIsInstance(nbk.nb_manufacturer, Manufacturer)
        self.assertEqual(nbk.nb_manufacturer.slug, slugify(onboarding_kwargs["netdev_vendor"]))

    def test_ensure_device_manufacturer_loose_missing(self):
        """Verify ensure_device_manufacturer function when Manufacturer object is not present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "loose"
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_site_slug": self.site1.slug,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_manufacturer(create_manufacturer=False)
            self.assertEqual(exc_info.exception.message, "ERROR manufacturer not found: Cisco")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        nbk.ensure_device_manufacturer(create_manufacturer=True)
        self.assertIsInstance(nbk.nb_manufacturer, Manufacturer)
        self.assertEqual(nbk.nb_manufacturer.slug, slugify(onboarding_kwargs["netdev_vendor"]))

    def test_ensure_device_type_strict_missing(self):
        """Verify ensure_device_type function when DeviceType object is not present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "strict"
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_site_slug": self.site1.slug,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)
        nbk.nb_manufacturer = Manufacturer.objects.create(name="Cisco", slug="cisco")

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_type(create_device_type=False)
            self.assertEqual(exc_info.exception.message, "ERROR device type not found: CSR1000v")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        nbk.ensure_device_type(create_device_type=True)
        self.assertIsInstance(nbk.nb_device_type, DeviceType)
        self.assertEqual(nbk.nb_device_type.slug, slugify(onboarding_kwargs["netdev_model"]))

    def test_ensure_device_type_loose_missing(self):
        """Verify ensure_device_type function when DeviceType object is not present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "loose"
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_site_slug": self.site1.slug,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)
        nbk.nb_manufacturer = Manufacturer.objects.create(name="Cisco", slug="cisco")

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_type(create_device_type=False)
            self.assertEqual(exc_info.exception.message, "ERROR device type not found: CSR1000v")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        nbk.ensure_device_type(create_device_type=True)
        self.assertIsInstance(nbk.nb_device_type, DeviceType)
        self.assertEqual(nbk.nb_device_type.slug, slugify(onboarding_kwargs["netdev_model"]))

    def test_ensure_device_type_strict_present(self):
        """Verify ensure_device_type function when DeviceType object is already present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "strict"
        manufacturer = Manufacturer.objects.create(name="Juniper", slug="juniper")

        device_type = DeviceType.objects.create(slug="srx3600", model="SRX3600", manufacturer=manufacturer)

        onboarding_kwargs = {
            "netdev_hostname": "device2",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Juniper",
            "netdev_nb_device_type_slug": device_type.slug,
            "netdev_nb_site_slug": self.site1.slug,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)
        nbk.nb_manufacturer = manufacturer

        nbk.ensure_device_type(create_device_type=False)
        self.assertEqual(nbk.nb_device_type, device_type)

    def test_ensure_device_type_loose_present(self):
        """Verify ensure_device_type function when DeviceType object is already present."""
        PLUGIN_SETTINGS["object_match_strategy"] = "loose"
        manufacturer = Manufacturer.objects.create(name="Juniper", slug="juniper")

        device_type = DeviceType.objects.create(slug="srx3600", model="SRX3600", manufacturer=manufacturer)

        onboarding_kwargs = {
            "netdev_hostname": "device2",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Juniper",
            "netdev_nb_device_type_slug": device_type.slug,
            "netdev_nb_site_slug": self.site1.slug,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)
        nbk.nb_manufacturer = manufacturer

        nbk.ensure_device_type(create_device_type=False)
        self.assertEqual(nbk.nb_device_type, device_type)

    def test_ensure_device_role_not_exist(self):
        """Verify ensure_device_role function when DeviceRole does not already exist."""
        test_role_name = "mytestrole"

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": test_role_name,
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_nb_site_slug": self.site1.slug,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_role(create_device_role=False)
            self.assertEqual(exc_info.exception.message, f"ERROR device role not found: {test_role_name}")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        nbk.ensure_device_role(create_device_role=True)
        self.assertIsInstance(nbk.nb_device_role, DeviceRole)
        self.assertEqual(nbk.nb_device_role.slug, slugify(test_role_name))

    def test_ensure_device_role_exist(self):
        """Verify ensure_device_role function when DeviceRole exist but is not assigned to the OT."""
        device_role = DeviceRole.objects.create(name="Firewall", slug="firewall")

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": device_role.slug,
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_nb_site_slug": self.site1.slug,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)
        nbk.ensure_device_role(create_device_role=False)

        self.assertEqual(nbk.nb_device_role, device_role)

    #
    def test_ensure_device_role_assigned(self):
        """Verify ensure_device_role function when DeviceRole exist and is already assigned."""
        device_role = DeviceRole.objects.create(name="Firewall", slug="firewall")

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": device_role.slug,
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_nb_site_slug": self.site1.slug,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)
        nbk.ensure_device_role(create_device_role=True)

        self.assertEqual(nbk.nb_device_role, device_role)

    def test_ensure_device_instance_not_exist(self):
        """Verify ensure_device_instance function."""
        serial_number = "123456"
        platform_slug = "cisco_ios"
        hostname = "device1"

        onboarding_kwargs = {
            "netdev_hostname": hostname,
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_site_slug": self.site1.slug,
            "netdev_netmiko_device_type": platform_slug,
            "netdev_serial_number": serial_number,
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": "GigaEthernet0",
            "netdev_mgmt_pflen": 24,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)

        nbk.ensure_device()

        self.assertIsInstance(nbk.device, Device)
        self.assertEqual(nbk.device.name, hostname)
        self.assertEqual(nbk.device.status, PLUGIN_SETTINGS["default_device_status"])
        self.assertEqual(nbk.device.platform.slug, platform_slug)
        self.assertEqual(nbk.device.serial, serial_number)

    def test_ensure_device_instance_exist(self):
        """Verify ensure_device_instance function."""
        manufacturer = Manufacturer.objects.create(name="Cisco", slug="cisco")

        device_role = DeviceRole.objects.create(name="Switch", slug="switch")

        device_type = DeviceType.objects.create(slug="c2960", model="c2960", manufacturer=manufacturer)

        device_name = "test_name"

        device = Device.objects.create(
            name=device_name,
            site=self.site1,
            device_type=device_type,
            device_role=device_role,
            status="planned",
            serial="987654",
        )

        onboarding_kwargs = {
            "netdev_hostname": device_name,
            "netdev_nb_role_slug": "switch",
            "netdev_vendor": "Cisco",
            "netdev_model": "c2960",
            "netdev_nb_site_slug": self.site1.slug,
            "netdev_netmiko_device_type": "cisco_ios",
            "netdev_serial_number": "123456",
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": "GigaEthernet0",
            "netdev_mgmt_pflen": 24,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)

        nbk.ensure_device()

        self.assertIsInstance(nbk.device, Device)
        self.assertEqual(nbk.device.pk, device.pk)

        self.assertEqual(nbk.device.name, device_name)
        self.assertEqual(nbk.device.platform.slug, "cisco_ios")
        self.assertEqual(nbk.device.serial, "123456")

    def test_ensure_interface_not_exist(self):
        """Verify ensure_interface function when the interface do not exist."""
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_site_slug": self.site1.slug,
            "netdev_netmiko_device_type": "cisco_ios",
            "netdev_serial_number": "123456",
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": "ge-0/0/0",
            "netdev_mgmt_pflen": 24,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)
        nbk.ensure_device()

        self.assertIsInstance(nbk.nb_mgmt_ifname, Interface)
        self.assertEqual(nbk.nb_mgmt_ifname.name, "ge-0/0/0")

    def test_ensure_interface_exist(self):
        """Verify ensure_interface function when the interface already exist."""
        manufacturer = Manufacturer.objects.create(name="Cisco", slug="cisco")

        device_role = DeviceRole.objects.create(name="Switch", slug="switch")

        device_type = DeviceType.objects.create(slug="c2960", model="c2960", manufacturer=manufacturer)

        device_name = "test_name"
        netdev_mgmt_ifname = "GigaEthernet0"

        device = Device.objects.create(
            name=device_name,
            site=self.site1,
            device_type=device_type,
            device_role=device_role,
            status="planned",
            serial="987654",
        )

        intf = Interface.objects.create(name=netdev_mgmt_ifname, device=device)

        onboarding_kwargs = {
            "netdev_hostname": device_name,
            "netdev_nb_role_slug": "switch",
            "netdev_vendor": "Cisco",
            "netdev_model": "c2960",
            "netdev_nb_site_slug": self.site1.slug,
            "netdev_netmiko_device_type": "cisco_ios",
            "netdev_serial_number": "123456",
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": netdev_mgmt_ifname,
            "netdev_mgmt_pflen": 24,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)

        nbk.ensure_device()

        self.assertEqual(nbk.nb_mgmt_ifname, intf)

    def test_ensure_primary_ip_not_exist(self):
        """Verify ensure_primary_ip function when the IP address do not already exist."""
        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_site_slug": self.site1.slug,
            "netdev_netmiko_device_type": "cisco_ios",
            "netdev_serial_number": "123456",
            "netdev_mgmt_ip_address": "192.0.2.10",
            "netdev_mgmt_ifname": "ge-0/0/0",
            "netdev_mgmt_pflen": 24,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)
        nbk.ensure_device()

        self.assertIsInstance(nbk.nb_primary_ip, IPAddress)
        self.assertIn(nbk.nb_primary_ip, Interface.objects.get(device=nbk.device, name="ge-0/0/0").ip_addresses.all())
        self.assertEqual(nbk.device.primary_ip, nbk.nb_primary_ip)

    def test_ensure_device_platform_missing(self):
        """Verify ensure_device_platform function when Platform object is not present."""
        platform_name = "cisco_ios"

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_site_slug": self.site1.slug,
            "netdev_nb_platform_slug": platform_name,
            "netdev_netmiko_device_type": platform_name,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)

        with self.assertRaises(OnboardException) as exc_info:
            nbk.ensure_device_platform(create_platform_if_missing=False)
            self.assertEqual(exc_info.exception.message, f"ERROR device platform not found: {platform_name}")
            self.assertEqual(exc_info.exception.reason, "fail-config")

        nbk.ensure_device_platform(create_platform_if_missing=True)
        self.assertIsInstance(nbk.nb_platform, Platform)
        self.assertEqual(nbk.nb_platform.slug, slugify(platform_name))

    def test_ensure_platform_present(self):
        """Verify ensure_device_platform function when Platform object is present."""
        platform_name = "juniper_junos"

        manufacturer = Manufacturer.objects.create(name="Juniper", slug="juniper")

        device_type = DeviceType.objects.create(slug="srx3600", model="SRX3600", manufacturer=manufacturer)

        platform = Platform.objects.create(slug=platform_name, name=platform_name,)

        onboarding_kwargs = {
            "netdev_hostname": "device2",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Juniper",
            "netdev_nb_device_type_slug": device_type.slug,
            "netdev_nb_site_slug": self.site1.slug,
            "netdev_nb_platform_slug": platform_name,
        }

        nbk = NetboxKeeper(**onboarding_kwargs)

        nbk.ensure_device_platform(create_platform_if_missing=False)

        self.assertIsInstance(nbk.nb_platform, Platform)
        self.assertEqual(nbk.nb_platform, platform)
        self.assertEqual(nbk.nb_platform.slug, slugify(platform_name))

    def test_platform_map(self):
        """Verify platform mapping of netmiko to slug functionality."""
        # Create static mapping
        PLUGIN_SETTINGS["platform_map"] = {"cisco_ios": "ios", "arista_eos": "eos", "cisco_nxos": "cisco-nxos"}

        onboarding_kwargs = {
            "netdev_hostname": "device1",
            "netdev_nb_role_slug": PLUGIN_SETTINGS["default_device_role"],
            "netdev_vendor": "Cisco",
            "netdev_model": "CSR1000v",
            "netdev_nb_site_slug": self.site1.slug,
            "netdev_netmiko_device_type": "cisco_ios",
        }

        nbk = NetboxKeeper(**onboarding_kwargs)

        nbk.ensure_device_platform(create_platform_if_missing=True)
        self.assertIsInstance(nbk.nb_platform, Platform)
        self.assertEqual(nbk.nb_platform.slug, slugify(PLUGIN_SETTINGS["platform_map"]["cisco_ios"]))
        self.assertEqual(
            Platform.objects.get(name=PLUGIN_SETTINGS["platform_map"]["cisco_ios"]).name,
            slugify(PLUGIN_SETTINGS["platform_map"]["cisco_ios"]),
        )
