"""Worker code for processing inbound OnboardingTasks.

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

import logging
import re

from dcim.models import Manufacturer, Device, Interface, DeviceType, DeviceRole
from django.conf import settings
from django.utils.text import slugify
from ipam.models import IPAddress

__all__ = []

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["netbox_onboarding"]


class NetboxKeeper:
    """Used to manage the information relating to the network device within the NetBox server."""

    def __init__(
            netdev_hostname=None,
            netdev_vendor=None,
            netdev_model=None,
            netdev_serial_number=None,
            netdev_mgmt_ifname=None,
            netdev_mgmt_pflen=None,
            netdev_mgmt_ip_address=None,
            netdev_nb_device_type_char=None,
            netdev_nb_role_slug=None,
            netdev_nb_site_slug=None,
            netdev_nb_platform_slug=None,
    ):
        """Create an instance and initialize the managed attributes that are used throughout the onboard processing.

        Args:
          netdev (NetdevKeeper): instance
        """
        self.netdev_hostname = netdev_hostname
        self.netdev_vendor = netdev_vendor
        self.netdev_model = netdev_model
        self.netdev_serial_number = netdev_serial_number
        self.netdev_mgmt_ifname = netdev_mgmt_ifname
        self.netdev_mgmt_pflen = netdev_mgmt_pflen
        self.netdev_mgmt_ip_address = netdev_mgmt_ip_address

        self.netdev_nb_device_char = netdev_nb_device_type_char
        self.netdev_nb_role_slug = netdev_nb_role_slug
        self.netdev_nb_site_slug = netdev_nb_site_slug
        self.netdev_nb_platform_slug = netdev_nb_platform_slug

        # these attributes are netbox model instances as discovered/created
        # through the course of processing.
        self.manufacturer = None
        self.device_type = None
        self.device = None
        self.interface = None
        self.primary_ip = None

    def ensure_device_type(
        self,
        create_manufacturer=PLUGIN_SETTINGS["create_manufacturer_if_missing"],
        create_device_type=PLUGIN_SETTINGS["create_device_type_if_missing"],
    ):
        """Ensure the Device Type (slug) exists in NetBox associated to the netdev "model" and "vendor" (manufacturer).

        Args:
          create_manufacturer (bool) :Flag to indicate if we need to create the manufacturer, if not already present
          create_device_type (bool): Flag to indicate if we need to create the device_type, if not already present
        Raises:
          OnboardException('fail-config'):
            When the device vendor value does not exist as a Manufacturer in
            NetBox.

          OnboardException('fail-config'):
            When the device-type exists by slug, but is assigned to a different
            manufacturer.  This should *not* happen, but guard-rail checking
            regardless in case two vendors have the same model name.
        """
        # First ensure that the vendor, as extracted from the network device exists
        # in NetBox.  We need the ID for this vendor when ensuring the DeviceType
        # instance.

        try:
            self.manufacturer = Manufacturer.objects.get(slug=slugify(self.netdev_vendor))
        except Manufacturer.DoesNotExist:
            if not create_manufacturer:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR manufacturer not found: {self.netdev_vendor}"
                )

            self.manufacturer = Manufacturer.objects.create(name=self.netdev_vendor, slug=slugify(self.netdev_vendor))
            self.manufacturer.save()

        # Now see if the device type (slug) already exists,
        #  if so check to make sure that it is not assigned as a different manufacturer
        # if it doesn't exist, create it if the flag 'create_device_type_if_missing' is defined

        slug = self.netdev_model
        if re.search(r"[^a-zA-Z0-9\-_]+", slug):
            logging.warning("device model is not sluggable: %s", slug)
            self.netdev_model = slug.replace(" ", "-")
            logging.warning("device model is now: %s", self.netdev_model)

        try:
            self.device_type = DeviceType.objects.get(slug=slugify(self.netdev_model))
            self.netdev_ot_device_type = self.device_type.slug
            #mzb# self.netdev.ot.save()
        except DeviceType.DoesNotExist:
            if not create_device_type:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR device type not found: {self.netdev_model}"
                )

            logging.info("CREATE: device-type: %s", self.netdev_model)
            self.device_type = DeviceType.objects.create(
                slug=slugify(self.netdev_model), model=self.netdev_model.upper(), manufacturer=self.manufacturer
            )
            self.device_type.save()
            self.netdev_ot_device_type = self.device_type.slug
            #mzb# self.netdev.ot.save()
            return

        if self.device_type.manufacturer.id != self.manufacturer.id:
            raise OnboardException(
                reason="fail-config",
                message=f"ERROR device type {self.netdev_model} already exists for vendor {self.netdev_vendor}",
            )

    def ensure_device_role(
        self,
        create_device_role=PLUGIN_SETTINGS["create_device_role_if_missing"],
        default_device_role=PLUGIN_SETTINGS["default_device_role"],
        default_device_role_color=PLUGIN_SETTINGS["default_device_role_color"],
    ):
        """Ensure that the device role is defined / exist in NetBox or create it if it doesn't exist.

        Args:
          create_device_role (bool) :Flag to indicate if we need to create the device_role, if not already present
          default_device_role (str): Default value for the device_role, if we need to create it
          default_device_role_color (str): Default color to assign to the device_role, if we need to create it
        Raises:
          OnboardException('fail-config'):
            When the device role value does not exist
            NetBox.
        """
        if self.netdev_ot_role:
            return

        try:
            device_role = DeviceRole.objects.get(slug=slugify(default_device_role))
        except DeviceRole.DoesNotExist:
            if not create_device_role:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR device role not found: {default_device_role}"
                )

            device_role = DeviceRole.objects.create(
                name=default_device_role,
                slug=slugify(default_device_role),
                color=default_device_role_color,
                vm_role=False,
            )
            device_role.save()

        self.netdev_ot_role = device_role
        #mzb# self.netdev.ot.save()
        return

    def ensure_device_instance(self, default_status=PLUGIN_SETTINGS["default_device_status"]):
        """Ensure that the device instance exists in NetBox and is assigned the provided device role or DEFAULT_ROLE.

        Args:
          default_status (str) : status assigned to a new device by default.
        """
        try:
            device = Device.objects.get(name=self.netdev_hostname, site=self.netdev_ot_site)
        except Device.DoesNotExist:
            device = Device.objects.create(
                name=self.netdev_hostname,
                site=self.netdev_ot_site,
                device_type=self.device_type,
                device_role=self.netdev_ot_role,
                status=default_status,
            )

        device.platform = self.netdev_ot_platform
        device.serial = self.netdev_serial_number
        device.save()

        # TODO:
        #mzb# ?
        #mzb# self.netdev.ot.created_device = device
        #mzb# self.netdev.ot.save()

        self.device = device

    def ensure_interface(self):
        """Ensure that the interface associated with the mgmt_ipaddr exists and is assigned to the device."""
        self.interface, _ = Interface.objects.get_or_create(name=self.netdev_mgmt_ifname, device=self.device)

    def ensure_primary_ip(self):
        """Ensure mgmt_ipaddr exists in IPAM, has the device interface, and is assigned as the primary IP address."""
        mgmt_ipaddr = self.netdev_ot_ip_address

        # see if the primary IP address exists in IPAM
        self.primary_ip, created = IPAddress.objects.get_or_create(address=f"{mgmt_ipaddr}/{self.netdev_mgmt_pflen}")

        if created or not self.primary_ip.interface:
            logging.info("ASSIGN: IP address %s to %s", self.primary_ip.address, self.interface.name)
            self.primary_ip.interface = self.interface

        self.primary_ip.save()

        # Ensure the primary IP is assigned to the device
        self.device.primary_ip4 = self.primary_ip
        self.device.save()

    def ensure_device(self):
        """Ensure that the device represented by the DevNetKeeper exists in the NetBox system."""
        self.ensure_device_type()
        self.ensure_device_role()
        self.ensure_device_instance()
        if PLUGIN_SETTINGS["create_management_interface_if_missing"]:
            self.ensure_interface()
            self.ensure_primary_ip()
