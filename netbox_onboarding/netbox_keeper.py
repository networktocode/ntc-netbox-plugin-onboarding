"""NetBox Keeper.

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

from django.conf import settings
from django.utils.text import slugify
from dcim.models import Manufacturer, Device, Interface, DeviceType, DeviceRole
from dcim.models import Platform
from dcim.models import Site
from ipam.models import IPAddress

from .constants import NETMIKO_TO_NAPALM_STATIC
from .exceptions import OnboardException

logger = logging.getLogger("rq.worker")

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["netbox_onboarding"]


def object_match(obj, search_array):
    """Used to search models for multiple criteria.

    Inputs:
        obj:            The model used for searching.
        search_array:   Nested dictionaries used to search models. First criteria will be used
                        for strict searching. Loose searching will loop through the search_array
                        until it finds a match. Example below.
                        [
                            {"slug__iexact": 'switch1'},
                            {"model__iexact": 'Cisco'}
                        ]
    """
    try:
        result = obj.objects.get(**search_array[0])
        return result
    except obj.DoesNotExist:
        if PLUGIN_SETTINGS["object_match_strategy"] == "loose":
            for search_array_element in search_array[1:]:
                try:
                    result = obj.objects.get(**search_array_element)
                    return result
                except obj.DoesNotExist:
                    pass
                except obj.MultipleObjectsReturned:
                    raise OnboardException(
                        reason="fail-general",
                        message=f"ERROR multiple objects found in {str(obj)} searching on {str(search_array_element)})",
                    )
        raise
    except obj.MultipleObjectsReturned:
        raise OnboardException(
            reason="fail-general",
            message=f"ERROR multiple objects found in {str(obj)} searching on {str(search_array_element)})",
        )


class NetboxKeeper:
    """Used to manage the information relating to the network device within the NetBox server."""

    def __init__(  # pylint: disable=R0913,R0914
        self,
        netdev_hostname,
        netdev_nb_role_slug,
        netdev_vendor,
        netdev_nb_site_slug,
        netdev_nb_device_type_slug=None,
        netdev_model=None,
        netdev_nb_role_color=None,
        netdev_mgmt_ip_address=None,
        netdev_nb_platform_slug=None,
        netdev_serial_number=None,
        netdev_mgmt_ifname=None,
        netdev_mgmt_pflen=None,
        netdev_netmiko_device_type=None,
        onboarding_class=None,
        driver_addon_result=None,
    ):
        """Create an instance and initialize the managed attributes that are used throughout the onboard processing.

        Args:
            netdev_hostname (str): NetBox's device name
            netdev_nb_role_slug (str): NetBox's device role slug
            netdev_vendor (str): Device's vendor name
            netdev_nb_site_slug (str): Device site's slug
            netdev_nb_device_type_slug (str): Device type's slug
            netdev_model (str): Device's model
            netdev_nb_role_color (str): NetBox device's role color
            netdev_mgmt_ip_address (str): IPv4 Address of a device
            netdev_nb_platform_slug (str): NetBox device's platform slug
            netdev_serial_number (str): Device's serial number
            netdev_mgmt_ifname (str): Device's management interface name
            netdev_mgmt_pflen (str): Device's management IP prefix-len
            netdev_netmiko_device_type (str): Device's Netmiko device type
            onboarding_class (Object): Onboarding Class (future use)
            driver_addon_result (Any): Attached extended result (future use)
        """
        self.netdev_mgmt_ip_address = netdev_mgmt_ip_address
        self.netdev_nb_site_slug = netdev_nb_site_slug
        self.netdev_nb_device_type_slug = netdev_nb_device_type_slug
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

        self.onboarding_class = onboarding_class
        self.driver_addon_result = driver_addon_result

        # these attributes are netbox model instances as discovered/created
        # through the course of processing.
        self.nb_site = None
        self.nb_manufacturer = None
        self.nb_device_type = None
        self.nb_device_role = None
        self.nb_platform = None

        self.device = None
        self.onboarded_device = None
        self.nb_mgmt_ifname = None
        self.nb_primary_ip = None

    def ensure_onboarded_device(self):
        """Lookup if the device already exists in the NetBox.

        Lookup is performed by querying for the IP address of the onboarded device.
        If the device with a given IP is already in NetBox, its attributes including name could be updated
        """
        try:
            if self.netdev_mgmt_ip_address:
                self.onboarded_device = Device.objects.get(primary_ip4__address__net_host=self.netdev_mgmt_ip_address)
        except Device.DoesNotExist:
            logger.info(
                "Could not find existing NetBox device for requested primary IP address (%s)",
                self.netdev_mgmt_ip_address,
            )
        except Device.MultipleObjectsReturned:
            raise OnboardException(
                reason="fail-general",
                message=f"ERROR multiple devices using same IP in NetBox: {self.netdev_mgmt_ip_address}",
            )

    def ensure_device_site(self):
        """Ensure device's site."""
        try:
            self.nb_site = Site.objects.get(slug=self.netdev_nb_site_slug)
        except Site.DoesNotExist:
            raise OnboardException(reason="fail-config", message=f"Site not found: {self.netdev_nb_site_slug}")

    def ensure_device_manufacturer(
        self,
        create_manufacturer=PLUGIN_SETTINGS["create_manufacturer_if_missing"],
        skip_manufacturer_on_update=PLUGIN_SETTINGS["skip_manufacturer_on_update"],
    ):
        """Ensure device's manufacturer."""
        # Support to skip manufacturer updates for existing devices
        if self.onboarded_device and skip_manufacturer_on_update:
            self.nb_manufacturer = self.onboarded_device.device_type.manufacturer

            return

        # First ensure that the vendor, as extracted from the network device exists
        # in NetBox.  We need the ID for this vendor when ensuring the DeviceType
        # instance.

        nb_manufacturer_slug = slugify(self.netdev_vendor)

        try:
            search_array = [{"slug__iexact": nb_manufacturer_slug}]
            self.nb_manufacturer = object_match(Manufacturer, search_array)
        except Manufacturer.DoesNotExist:
            if create_manufacturer:
                self.nb_manufacturer = Manufacturer.objects.create(name=self.netdev_vendor, slug=nb_manufacturer_slug)
            else:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR manufacturer not found: {self.netdev_vendor}"
                )

    def ensure_device_type(
        self,
        create_device_type=PLUGIN_SETTINGS["create_device_type_if_missing"],
        skip_device_type_on_update=PLUGIN_SETTINGS["skip_device_type_on_update"],
    ):
        """Ensure the Device Type (slug) exists in NetBox associated to the netdev "model" and "vendor" (manufacturer).

        Args:
          create_device_type (bool): Flag to indicate if we need to create the device_type, if not already present
          skip_device_type_on_update (bool): Flag to indicate if we skip device type updates for existing devices
        Raises:
          OnboardException('fail-config'):
            When the device vendor value does not exist as a Manufacturer in
            NetBox.

          OnboardException('fail-config'):
            When the device-type exists by slug, but is assigned to a different
            manufacturer.  This should *not* happen, but guard-rail checking
            regardless in case two vendors have the same model name.
        """
        # Support to skip device type updates for existing devices
        if self.onboarded_device and skip_device_type_on_update:
            self.nb_device_type = self.onboarded_device.device_type

            return

        # Now see if the device type (slug) already exists,
        #  if so check to make sure that it is not assigned as a different manufacturer
        # if it doesn't exist, create it if the flag 'create_device_type_if_missing' is defined

        slug = self.netdev_model
        if self.netdev_model and re.search(r"[^a-zA-Z0-9\-_]+", slug):
            logger.warning("device model is not sluggable: %s", slug)
            self.netdev_model = slug.replace(" ", "-")
            logger.warning("device model is now: %s", self.netdev_model)

        # Use declared device type or auto-discovered model
        nb_device_type_text = self.netdev_nb_device_type_slug or self.netdev_model

        if not nb_device_type_text:
            raise OnboardException(reason="fail-config", message="ERROR device type not found")

        nb_device_type_slug = slugify(nb_device_type_text)

        try:
            search_array = [
                {"slug__iexact": nb_device_type_slug},
                {"model__iexact": self.netdev_model},
                {"part_number__iexact": self.netdev_model},
            ]

            self.nb_device_type = object_match(DeviceType, search_array)

            if self.nb_device_type.manufacturer.id != self.nb_manufacturer.id:
                raise OnboardException(
                    reason="fail-config",
                    message=f"ERROR device type {self.netdev_model} " f"already exists for vendor {self.netdev_vendor}",
                )

        except DeviceType.DoesNotExist:
            if create_device_type:
                logger.info("CREATE: device-type: %s", self.netdev_model)
                self.nb_device_type = DeviceType.objects.create(
                    slug=nb_device_type_slug, model=nb_device_type_slug.upper(), manufacturer=self.nb_manufacturer,
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
            self.netdev_nb_platform_slug = (
                self.netdev_nb_platform_slug
                or PLUGIN_SETTINGS["platform_map"].get(self.netdev_netmiko_device_type)
                or self.netdev_netmiko_device_type
            )

            if not self.netdev_nb_platform_slug:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR device platform not found: {self.netdev_hostname}"
                )

            self.nb_platform = Platform.objects.get(slug=self.netdev_nb_platform_slug)

            logger.info("PLATFORM: found in NetBox %s", self.netdev_nb_platform_slug)

        except Platform.DoesNotExist:
            if create_platform_if_missing:
                platform_to_napalm_netbox = {
                    platform.slug: platform.napalm_driver
                    for platform in Platform.objects.all()
                    if platform.napalm_driver
                }

                # Update Constants if Napalm driver is defined for NetBox Platform
                netmiko_to_napalm = {**NETMIKO_TO_NAPALM_STATIC, **platform_to_napalm_netbox}

                self.nb_platform = Platform.objects.create(
                    name=self.netdev_nb_platform_slug,
                    slug=self.netdev_nb_platform_slug,
                    napalm_driver=netmiko_to_napalm[self.netdev_netmiko_device_type],
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
        if self.onboarded_device:
            # Construct lookup arguments if onboarded device already exists in NetBox

            logger.info(
                "Found existing NetBox device (%s) for requested primary IP address (%s)",
                self.onboarded_device.name,
                self.netdev_mgmt_ip_address,
            )
            lookup_args = {
                "pk": self.onboarded_device.pk,
                "defaults": dict(
                    name=self.netdev_hostname,
                    device_type=self.nb_device_type,
                    device_role=self.nb_device_role,
                    platform=self.nb_platform,
                    site=self.nb_site,
                    serial=self.netdev_serial_number,
                    # status= field is not updated in case of already existing devices to prevent changes
                ),
            }
        else:
            # Construct lookup arguments if onboarded device does not exist in NetBox

            lookup_args = {
                "name": self.netdev_hostname,
                "defaults": dict(
                    device_type=self.nb_device_type,
                    device_role=self.nb_device_role,
                    platform=self.nb_platform,
                    site=self.nb_site,
                    serial=self.netdev_serial_number,
                    # status= defined only for new devices, no update for existing should occur
                    status=default_status,
                ),
            }

        try:
            self.device, created = Device.objects.update_or_create(**lookup_args)

            if created:
                logger.info("CREATED device: %s", self.netdev_hostname)
            else:
                logger.info("GOT/UPDATED device: %s", self.netdev_hostname)

        except Device.MultipleObjectsReturned:
            raise OnboardException(
                reason="fail-general",
                message=f"ERROR multiple devices using same name in NetBox: {self.netdev_hostname}",
            )

    def ensure_interface(self):
        """Ensures that the interface associated with the mgmt_ipaddr exists and is assigned to the device."""
        if self.netdev_mgmt_ifname:
            self.nb_mgmt_ifname, _ = Interface.objects.get_or_create(name=self.netdev_mgmt_ifname, device=self.device)

    def ensure_primary_ip(self):
        """Ensure mgmt_ipaddr exists in IPAM, has the device interface, and is assigned as the primary IP address."""
        # see if the primary IP address exists in IPAM
        if self.netdev_mgmt_ip_address and self.netdev_mgmt_pflen:
            self.nb_primary_ip, created = IPAddress.objects.get_or_create(
                address=f"{self.netdev_mgmt_ip_address}/{self.netdev_mgmt_pflen}"
            )

            if created or not self.nb_primary_ip in self.nb_mgmt_ifname.ip_addresses.all():
                logger.info("ASSIGN: IP address %s to %s", self.nb_primary_ip.address, self.nb_mgmt_ifname.name)
                self.nb_mgmt_ifname.ip_addresses.add(self.nb_primary_ip)
                self.nb_mgmt_ifname.save()

            # Ensure the primary IP is assigned to the device
            self.device.primary_ip4 = self.nb_primary_ip
            self.device.save()

    def ensure_device(self):
        """Ensure that the device represented by the DevNetKeeper exists in the NetBox system."""
        self.ensure_onboarded_device()
        self.ensure_device_site()
        self.ensure_device_manufacturer()
        self.ensure_device_type()
        self.ensure_device_role()
        self.ensure_device_platform()
        self.ensure_device_instance()

        if PLUGIN_SETTINGS["create_management_interface_if_missing"]:
            self.ensure_interface()
            self.ensure_primary_ip()
