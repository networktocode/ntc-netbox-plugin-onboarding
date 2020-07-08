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
import socket

from napalm import get_network_driver
from napalm.base.exceptions import ConnectionException, CommandErrorException
import netaddr
from netaddr.core import AddrFormatError

from django.conf import settings
from django.utils.text import slugify

from netmiko.ssh_autodetect import SSHDetect
from netmiko.ssh_exception import NetMikoAuthenticationException
from netmiko.ssh_exception import NetMikoTimeoutException
from paramiko.ssh_exception import SSHException

from dcim.models import Manufacturer, Device, Interface, DeviceType, Platform, DeviceRole
from ipam.models import IPAddress

from .constants import NETMIKO_TO_NAPALM

__all__ = []

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["netbox_onboarding"]


class OnboardException(Exception):
    """A failure occurred during the onboarding process.

    The exception includes a reason "slug" as defined below as well as a humanized message.
    """

    REASONS = (
        "fail-config",  # config provided is not valid
        "fail-connect",  # device is unreachable at IP:PORT
        "fail-execute",  # unable to execute device/API command
        "fail-login",  # bad username/password
        "fail-dns",  # failed to get IP address from name resolution
        "fail-general",  # other error
    )

    def __init__(self, reason, message, **kwargs):
        super(OnboardException, self).__init__(kwargs)
        self.reason = reason
        self.message = message

    def __str__(self):
        return f"{self.__class__.__name__}: {self.reason}: {self.message}"


# -----------------------------------------------------------------------------
#
#                            Network Device Keeper
#
# -----------------------------------------------------------------------------


class NetdevKeeper:
    """Used to maintain information about the network device during the onboarding process."""

    def __init__(self, onboarding_task, username=None, password=None, secret=None):
        """Initialize the network device keeper instance and ensure the required configuration parameters are provided.

        Args:
          onboarding_task (OnboardingTask): Task being processed
          username (str): Device username (if unspecified, NAPALM_USERNAME settings variable will be used)
          password (str): Device password (if unspecified, NAPALM_PASSWORD settings variable will be used)
          secret (str): Device secret password (if unspecified, NAPALM_ARGS["secret"] settings variable will be used)

        Raises:
          OnboardException('fail-config'):
            When any required config options are missing.
        """
        self.ot = onboarding_task

        # Attributes that are set when reading info from device

        self.hostname = None
        self.vendor = None
        self.model = None
        self.serial_number = None
        self.mgmt_ifname = None
        self.mgmt_pflen = None
        self.username = username or settings.NAPALM_USERNAME
        self.password = password or settings.NAPALM_PASSWORD
        self.secret = secret or settings.NAPALM_ARGS.get("secret", None)

    def check_reachability(self):
        """Ensure that the device at the mgmt-ipaddr provided is reachable.

        We do this check before attempting other "show" commands so that we know we've got a
        device that can be reached.

        Raises:
          OnboardException('fail-connect'):
            When device unreachable
        """
        ip_addr = self.ot.ip_address
        port = self.ot.port
        timeout = self.ot.timeout

        logging.info("CHECK: IP %s:%s", ip_addr, port)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip_addr, port))

        except (socket.error, socket.timeout, ConnectionError):
            raise OnboardException(reason="fail-connect", message=f"ERROR device unreachable: {ip_addr}:{port}")

    @staticmethod
    def check_netmiko_conversion(guessed_device_type, platform_map=None):
        """Method to convert Netmiko device type into the mapped type if defined in the settings file.

        Args:
            guessed_device_type (string): Netmiko device type guessed platform
            test_platform_map (dict): Platform Map for use in testing

        Returns:
            string: Platform name
        """
        # If this is defined, process the mapping
        if platform_map:
            # Attempt to get a mapped slug. If there is no slug, return the guessed_device_type as the slug
            return platform_map.get(guessed_device_type, guessed_device_type)

        # There is no mapping configured, return what was brought in
        return guessed_device_type

    def guess_netmiko_device_type(self, **kwargs):
        """Guess the device type of host, based on Netmiko."""
        guessed_device_type = None

        remote_device = {
            "device_type": "autodetect",
            "host": kwargs.get("host"),
            "username": kwargs.get("username"),
            "password": kwargs.get("password"),
            "secret": kwargs.get("secret"),
        }

        try:
            logging.info("INFO guessing device type: %s", kwargs.get("host"))
            guesser = SSHDetect(**remote_device)
            guessed_device_type = guesser.autodetect()
            logging.info("INFO guessed device type: %s", guessed_device_type)

        except NetMikoAuthenticationException as err:
            logging.error("ERROR %s", err)
            raise OnboardException(reason="fail-login", message="ERROR {}".format(str(err)))

        except (NetMikoTimeoutException, SSHException) as err:
            logging.error("ERROR %s", err)
            raise OnboardException(reason="fail-connect", message="ERROR {}".format(str(err)))

        except Exception as err:
            logging.error("ERROR %s", err)
            raise OnboardException(reason="fail-general", message="ERROR {}".format(str(err)))

        logging.info("INFO device type is %s", guessed_device_type)

        # Get the platform map from the PLUGIN SETTINGS, Return the result of doing a check_netmiko_conversion
        return self.check_netmiko_conversion(guessed_device_type, platform_map=PLUGIN_SETTINGS.get("platform_map", {}))

    def get_platform_slug(self):
        """Get platform slug in netmiko format (ie cisco_ios, cisco_xr etc)."""
        if self.ot.platform:
            platform_slug = self.ot.platform.slug
        else:
            platform_slug = self.guess_netmiko_device_type(
                host=self.ot.ip_address, username=self.username, password=self.password, secret=self.secret,
            )

        logging.info("PLATFORM NAME is %s", platform_slug)

        return platform_slug

    @staticmethod
    def get_platform_object_from_netbox(
        platform_slug, create_platform_if_missing=PLUGIN_SETTINGS["create_platform_if_missing"]
    ):
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
            # Get the platform from the NetBox DB
            platform = Platform.objects.get(slug=platform_slug)
            logging.info("PLATFORM: found in NetBox %s", platform_slug)
        except Platform.DoesNotExist:

            if not create_platform_if_missing:
                raise OnboardException(
                    reason="fail-general", message=f"ERROR platform not found in NetBox: {platform_slug}"
                )

            if platform_slug not in NETMIKO_TO_NAPALM.keys():
                raise OnboardException(
                    reason="fail-general",
                    message=f"ERROR platform not found in NetBox and it's eligible for auto-creation: {platform_slug}",
                )

            platform = Platform.objects.create(
                name=platform_slug, slug=platform_slug, napalm_driver=NETMIKO_TO_NAPALM[platform_slug]
            )
            platform.save()

        else:
            if not platform.napalm_driver:
                raise OnboardException(
                    reason="fail-general", message=f"ERROR platform is missing the NAPALM Driver: {platform_slug}",
                )

        return platform

    def check_ip(self):
        """Method to check if the IP address form field was an IP address.

        If it is a DNS name, attempt to resolve the DNS address and assign the IP address to the
        name.

        Returns:
            (bool): True if the IP address is an IP address, or a DNS entry was found and
                    reassignment of the ot.ip_address was done.
                    False if unable to find a device IP (error)

        Raises:
          OnboardException("fail-general"):
            When a prefix was entered for an IP address
          OnboardException("fail-dns"):
            When a Name lookup via DNS fails to resolve an IP address
        """
        try:
            # Assign checked_ip to None for error handling
            # If successful, this is an IP address and can pass
            checked_ip = netaddr.IPAddress(self.ot.ip_address)
            return True
        # Catch when someone has put in a prefix address, raise an exception
        except ValueError:
            raise OnboardException(
                reason="fail-general", message=f"ERROR appears a prefix was entered: {self.ot.ip_address}"
            )
        # An AddrFormatError exception means that there is not an IP address in the field, and should continue on
        except AddrFormatError:
            try:
                # Do a lookup of name to get the IP address to connect to
                checked_ip = socket.gethostbyname(self.ot.ip_address)
                self.ot.ip_address = checked_ip
                return True
            except socket.gaierror:
                # DNS Lookup has failed, Raise an exception for unable to complete DNS lookup
                raise OnboardException(
                    reason="fail-dns", message=f"ERROR failed to complete DNS lookup: {self.ot.ip_address}"
                )

    def get_required_info(
        self,
        default_mgmt_if=PLUGIN_SETTINGS["default_management_interface"],
        default_mgmt_pfxlen=PLUGIN_SETTINGS["default_management_prefix_length"],
    ):
        """Gather information from the network device that is needed to onboard the device into the NetBox system.

        Raises:
          OnboardException('fail-login'):
            When unable to login to device

          OnboardException('fail-execute'):
            When unable to run commands to collect device information

          OnboardException('fail-general'):
            Any other unexpected device comms failure.
        """
        # Check to see if the IP address entered was an IP address or a DNS entry, get the IP address
        self.check_ip()
        self.check_reachability()
        mgmt_ipaddr = self.ot.ip_address

        logging.info("COLLECT: device information %s", mgmt_ipaddr)

        try:
            platform_slug = self.get_platform_slug()
            platform_object = self.get_platform_object_from_netbox(platform_slug=platform_slug)
            if self.ot.platform != platform_object:
                self.ot.platform = platform_object
                self.ot.save()

            driver_name = platform_object.napalm_driver

            if not driver_name:
                raise OnboardException(
                    reason="fail-general",
                    message=f"Onboarding for Platform {platform_slug} not supported, as it has no specified NAPALM driver",
                )

            driver = get_network_driver(driver_name)
            optional_args = settings.NAPALM_ARGS.copy()
            optional_args["secret"] = self.secret
            dev = driver(
                hostname=mgmt_ipaddr,
                username=self.username,
                password=self.password,
                timeout=self.ot.timeout,
                optional_args=optional_args,
            )

            dev.open()
            logging.info("COLLECT: device facts")
            facts = dev.get_facts()

            logging.info("COLLECT: device interface IPs")
            ip_ifs = dev.get_interfaces_ip()

        except ConnectionException as exc:
            raise OnboardException(reason="fail-login", message=exc.args[0])

        except CommandErrorException as exc:
            raise OnboardException(reason="fail-execute", message=exc.args[0])

        except Exception as exc:
            raise OnboardException(reason="fail-general", message=str(exc))

        # locate the interface assigned with the mgmt_ipaddr value and retain
        # the interface name and IP prefix-length so that we can use it later
        # when creating the IPAM IP-Address instance.
        # Note that in some cases (e.g., NAT) the mgmt_ipaddr may differ than
        # the interface addresses present on the device. We need to handle this.

        def get_mgmt_info():
            """Get the interface name and prefix length for the management interface."""
            for if_name, if_data in ip_ifs.items():
                for if_addr, if_addr_data in if_data["ipv4"].items():
                    if if_addr == mgmt_ipaddr:
                        return (if_name, if_addr_data["prefix_length"])
            return (default_mgmt_if, default_mgmt_pfxlen)

        # retain the attributes that will be later used by NetBox processing.

        self.hostname = facts["hostname"]
        self.vendor = facts["vendor"].title()
        self.model = facts["model"].lower()
        self.serial_number = facts["serial_number"]
        self.mgmt_ifname, self.mgmt_pflen = get_mgmt_info()


# -----------------------------------------------------------------------------
#
#                            NetBox Device Keeper
#
# -----------------------------------------------------------------------------


class NetboxKeeper:
    """Used to manage the information relating to the network device within the NetBox server."""

    def __init__(self, netdev):
        """Create an instance and initialize the managed attributes that are used throughout the onboard processing.

        Args:
          netdev (NetdevKeeper): instance
        """
        self.netdev = netdev

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
            self.manufacturer = Manufacturer.objects.get(slug=slugify(self.netdev.vendor))
        except Manufacturer.DoesNotExist:
            if not create_manufacturer:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR manufacturer not found: {self.netdev.vendor}"
                )

            self.manufacturer = Manufacturer.objects.create(name=self.netdev.vendor, slug=slugify(self.netdev.vendor))
            self.manufacturer.save()

        # Now see if the device type (slug) already exists,
        #  if so check to make sure that it is not assigned as a different manufacturer
        # if it doesn't exist, create it if the flag 'create_device_type_if_missing' is defined

        slug = self.netdev.model
        if re.search(r"[^a-zA-Z0-9\-_]+", slug):
            logging.warning("device model is not sluggable: %s", slug)
            self.netdev.model = slug.replace(" ", "-")
            logging.warning("device model is now: %s", self.netdev.model)

        try:
            self.device_type = DeviceType.objects.get(slug=slugify(self.netdev.model))
            self.netdev.ot.device_type = self.device_type.slug
            self.netdev.ot.save()
        except DeviceType.DoesNotExist:
            if not create_device_type:
                raise OnboardException(
                    reason="fail-config", message=f"ERROR device type not found: {self.netdev.model}"
                )

            logging.info("CREATE: device-type: %s", self.netdev.model)
            self.device_type = DeviceType.objects.create(
                slug=slugify(self.netdev.model), model=self.netdev.model.upper(), manufacturer=self.manufacturer
            )
            self.device_type.save()
            self.netdev.ot.device_type = self.device_type.slug
            self.netdev.ot.save()
            return

        if self.device_type.manufacturer.id != self.manufacturer.id:
            raise OnboardException(
                reason="fail-config",
                message=f"ERROR device type {self.netdev.model} already exists for vendor {self.netdev.vendor}",
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
        if self.netdev.ot.role:
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

        self.netdev.ot.role = device_role
        self.netdev.ot.save()
        return

    def ensure_device_instance(self, default_status=PLUGIN_SETTINGS["default_device_status"]):
        """Ensure that the device instance exists in NetBox and is assigned the provided device role or DEFAULT_ROLE.

        Args:
          default_status (str) : status assigned to a new device by default.
        """
        try:
            device = Device.objects.get(name=self.netdev.hostname, site=self.netdev.ot.site)
        except Device.DoesNotExist:
            device = Device.objects.create(
                name=self.netdev.hostname,
                site=self.netdev.ot.site,
                device_type=self.device_type,
                device_role=self.netdev.ot.role,
                status=default_status,
            )

        device.platform = self.netdev.ot.platform
        device.serial = self.netdev.serial_number
        device.save()

        self.netdev.ot.created_device = device
        self.netdev.ot.save()

        self.device = device

    def ensure_interface(self):
        """Ensure that the interface associated with the mgmt_ipaddr exists and is assigned to the device."""
        self.interface, _ = Interface.objects.get_or_create(name=self.netdev.mgmt_ifname, device=self.device)

    def ensure_primary_ip(self):
        """Ensure mgmt_ipaddr exists in IPAM, has the device interface, and is assigned as the primary IP address."""
        mgmt_ipaddr = self.netdev.ot.ip_address

        # see if the primary IP address exists in IPAM
        self.primary_ip, created = IPAddress.objects.get_or_create(address=f"{mgmt_ipaddr}/{self.netdev.mgmt_pflen}")

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
