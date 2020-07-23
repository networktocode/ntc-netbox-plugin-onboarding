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
from dcim.models import Platform
from dcim.models import Site
from django.conf import settings
from django.utils.text import slugify
from ipam.models import IPAddress

from .constants import NETMIKO_TO_NAPALM

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["netbox_onboarding"]


from .exceptions import OnboardException


class NetboxKeeper:
    """Used to manage the information relating to the network device within the NetBox server."""

    def __init__(
        self,
        netdev_hostname,
        netdev_nb_role_slug,
        netdev_vendor,
        netdev_nb_site_slug,
        netdev_nb_device_type_char=None,
        netdev_model=None,
        netdev_nb_role_color=None,
        netdev_mgmt_ip_address=None,
        netdev_nb_platform_slug=None,
        netdev_serial_number=None,
        netdev_mgmt_ifname=None,
        netdev_mgmt_pflen=None,
        netdev_netmiko_device_type=None,
    ):
        """Create an instance and initialize the managed attributes that are used throughout the onboard processing.

        Args:
          netdev (NetdevKeeper): instance
        """
        self.netdev_mgmt_ip_address = netdev_mgmt_ip_address
        self.netdev_nb_site_slug = netdev_nb_site_slug
        self.netdev_nb_device_type_char = netdev_nb_device_type_char
        self.netdev_nb_role_slug = netdev_nb_role_slug
        self.netdev_nb_role_color = netdev_nb_role_color
        self.netdev_nb_platform_slug = netdev_nb_platform_slug

        self.netdev_hostname = netdev_hostname
        self.netdev_vendor = netdev_vendor
        self.netdev_model = netdev_model
        self.netdev_serial_number = netdev_serial_number
        self.netdev_mgmt_ifname = netdev_mgmt_ifname
        self.netdev_mgmt_pflen = netdev_mgmt_pflen
        self.netdev_netmiko_device_type = netdev_netmiko_device_type

        # these attributes are netbox model instances as discovered/created
        # through the course of processing.
        self.nb_site = None
        self.nb_manufacturer = None
        self.nb_device_type = None
        self.nb_device_role = None
        self.nb_platform = None

        self.device = None
        self.nb_mgmt_ifname = None
        self.nb_primary_ip = None

    def ensure_device_site(self):
        try:
            self.nb_site = Site.objects.get(slug=self.netdev_nb_site_slug)
        except Site.DoesNotExist:
            raise OnboardException(reason="fail-config", message=f"Site not found: {self.netdev_nb_site_slug}")

    def ensure_device_manufacturer(
        self, create_manufacturer=PLUGIN_SETTINGS["create_manufacturer_if_missing"],
    ):
        # First ensure that the vendor, as extracted from the network device exists
        # in NetBox.  We need the ID for this vendor when ensuring the DeviceType
        # instance.

        nb_manufacturer_slug = slugify(self.netdev_vendor)

        try:
            self.nb_manufacturer = Manufacturer.objects.get(slug=nb_manufacturer_slug)
        except Manufacturer.DoesNotExist:
            if create_manufacturer:
                self.nb_manufacturer = Manufacturer.objects.create(name=self.netdev_vendor, slug=nb_manufacturer_slug)
            else:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR manufacturer not found: {self.netdev_vendor}"
                )

    def ensure_device_type(
        self, create_device_type=PLUGIN_SETTINGS["create_device_type_if_missing"],
    ):
        """Ensure the Device Type (slug) exists in NetBox associated to the netdev "model" and "vendor" (manufacturer).

        Args:
          #create_manufacturer (bool) :Flag to indicate if we need to create the manufacturer, if not already present
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
        # Now see if the device type (slug) already exists,
        #  if so check to make sure that it is not assigned as a different manufacturer
        # if it doesn't exist, create it if the flag 'create_device_type_if_missing' is defined

        slug = self.netdev_model
        if re.search(r"[^a-zA-Z0-9\-_]+", slug):
            logging.warning("device model is not sluggable: %s", slug)
            self.netdev_model = slug.replace(" ", "-")
            logging.warning("device model is now: %s", self.netdev_model)

        # Use declared device type or auto-discovered model
        nb_device_type_text = self.netdev_nb_device_type_char or self.netdev_model

        if not nb_device_type_text:
            raise OnboardException(reason="fail-config", message=f"ERROR device type not found: {self.netdev_hostname}")

        nb_device_type_slug = slugify(nb_device_type_text)

        try:
            self.nb_device_type = DeviceType.objects.get(slug=nb_device_type_slug)

            if self.nb_device_type.manufacturer.id != self.nb_manufacturer.id:
                raise OnboardException(
                    reason="fail-config",
                    message=f"ERROR device type {self.netdev_model} " f"already exists for vendor {self.netdev_vendor}",
                )

        except DeviceType.DoesNotExist:
            if create_device_type:
                logging.info("CREATE: device-type: %s", self.netdev_model)
                self.nb_device_type = DeviceType.objects.create(
                    slug=nb_device_type_slug, model=self.netdev_model.upper(), manufacturer=self.nb_manufacturer,
                )
            else:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR device type not found: {self.netdev_model}"
                )

    def ensure_device_role(
        self, create_device_role=PLUGIN_SETTINGS["create_device_role_if_missing"],
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
        try:
            self.nb_device_role = DeviceRole.objects.get(slug=self.netdev_nb_role_slug)
        except DeviceRole.DoesNotExist:
            if create_device_role:
                self.nb_device_role = DeviceRole.objects.create(
                    name=self.netdev_nb_role_slug,
                    slug=self.netdev_nb_role_slug,
                    color=self.netdev_nb_role_color,
                    vm_role=False,
                )
            else:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR device role not found: {self.netdev_nb_role_slug}"
                )

    def ensure_device_platform(self, create_platform_if_missing=PLUGIN_SETTINGS["create_platform_if_missing"]):
        """Get platform object from NetBox filtered by platform_slug.

        Args:
            platform_slug (string): slug of a platform object present in NetBox, object will be created if not present
            and create_platform_if_missing is enabled

        Return:
            dcim.models.Platform object

        Raises:
            OnboardException

        Lookup is performed based on the object's slug field (not the name field)
        """

        try:
            self.netdev_nb_platform_slug = self.netdev_nb_platform_slug or self.netdev_netmiko_device_type

            if not self.netdev_nb_platform_slug:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR device platform not found: {self.netdev_hostname}"
                )

            self.nb_platform = Platform.objects.get(slug=self.netdev_nb_platform_slug)

            logging.info(f"PLATFORM: found in NetBox {self.netdev_nb_platform_slug}")

        except Platform.DoesNotExist:
            if create_platform_if_missing:
                self.nb_platform = Platform.objects.create(
                    name=self.netdev_nb_platform_slug,
                    slug=self.netdev_nb_platform_slug,
                    napalm_driver=NETMIKO_TO_NAPALM[self.netdev_netmiko_device_type],
                )
            else:
                raise OnboardException(
                    reason="fail-general", message=f"ERROR platform not found in NetBox: {self.netdev_nb_platform_slug}"
                )

    def ensure_device_instance(self, default_status=PLUGIN_SETTINGS["default_device_status"]):
        """Ensure that the device instance exists in NetBox and is assigned the provided device role or DEFAULT_ROLE.

        Args:
          default_status (str) : status assigned to a new device by default.
        """

        # Lookup if the device already exists in the NetBox
        # First update and creation lookup is by checking the IP address
        # of the onboarded device.
        #
        # If the device with a given IP is already in NetBox,
        # any attributes including name could be updated
        onboarded_device = None

        try:
            if self.netdev_mgmt_ip_address:
                onboarded_device = Device.objects.get(primary_ip4__address__net_host=self.netdev_mgmt_ip_address)
        except Device.DoesNotExist:
            logging.info(f"No devices found with primary-ip IP: " f"{self.netdev_mgmt_ip_address}")
        except Device.MultipleObjectsReturned:
            raise OnboardException(
                reason="fail-general",
                message=f"ERROR multiple devices using same IP in NetBox: " f"{self.netdev_mgmt_ip_address}",
            )

        if onboarded_device:
            logging.info(f"Found device with primary-ip IP: {onboarded_device.name}")
            lookup_args = {
                "pk": onboarded_device.pk,
                "defaults": dict(
                    name=self.netdev_hostname,
                    device_type=self.nb_device_type,
                    device_role=self.nb_device_role,
                    platform=self.nb_platform,
                    site=self.nb_site,
                    serial=self.netdev_serial_number,
                ),
            }
        else:
            lookup_args = {
                "name": self.netdev_hostname,
                "defaults": dict(
                    device_type=self.nb_device_type,
                    device_role=self.nb_device_role,
                    platform=self.nb_platform,
                    site=self.nb_site,
                    serial=self.netdev_serial_number,
                    status=default_status,
                ),
            }

        try:
            self.device, created = Device.objects.update_or_create(**lookup_args)

            if created:
                logging.info(f"CREATED device: {self.netdev_hostname}")
            else:
                logging.info(f"GOT/UPDATED device: {self.netdev_hostname}")

        except Device.MultipleObjectsReturned:
            raise OnboardException(
                reason="fail-general",
                message=f"ERROR multiple devices using same name in NetBox: {self.netdev_hostname}",
            )

    def ensure_interface(self):
        """
        Ensures that the interface associated with the mgmt_ipaddr exists and
        is assigned to the device.
        """
        self.nb_mgmt_ifname, created = Interface.objects.get_or_create(name=self.netdev_mgmt_ifname, device=self.device)

    def ensure_primary_ip(self):
        """
        Ensure mgmt_ipaddr exists in IPAM, has the device interface,
        and is assigned as the primary IP address.
        """
        # see if the primary IP address exists in IPAM
        self.nb_primary_ip, created = IPAddress.objects.get_or_create(
            address=f"{self.netdev_mgmt_ip_address}/{self.netdev_mgmt_pflen}"
        )

        if created or not self.nb_primary_ip.interface:
            logging.info("ASSIGN: IP address %s to %s", self.nb_primary_ip.address, self.nb_mgmt_ifname.name)
            self.nb_primary_ip.interface = self.nb_mgmt_ifname
            self.nb_primary_ip.save()

        # Ensure the primary IP is assigned to the device
        self.device.primary_ip4 = self.nb_primary_ip
        self.device.save()

    def ensure_device(self):
        """Ensure that the device represented by the DevNetKeeper exists in the NetBox system."""
        self.ensure_device_site()
        self.ensure_device_manufacturer()
        self.ensure_device_type()
        self.ensure_device_role()
        self.ensure_device_platform()
        self.ensure_device_instance()

        if PLUGIN_SETTINGS["create_management_interface_if_missing"]:
            self.ensure_interface()
            self.ensure_primary_ip()
