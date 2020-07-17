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

    def get_netdev_dict(self):
        netdev_dict = {
            'netdev_hostname': self.hostname,
            'netdev_vendor': self.vendor,
            'netdev_model': self.model,
            'netdev_serial_number': self.serial_number,
            'netdev_mgmt_ifname': self.mgmt_ifname,
            'netdev_mgmt_pflen': self.mgmt_pflen,
        }

        return netdev_dict
