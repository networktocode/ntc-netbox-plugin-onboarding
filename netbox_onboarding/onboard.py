"""
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
import socket
import re
import os
from first import first

from napalm import get_network_driver
from napalm.base.exceptions import ConnectionException, CommandErrorException

from dcim.models import Manufacturer, Device, Interface, DeviceType
from ipam.models import IPAddress

__all__ = []


class OnboardException(Exception):
    """
    Any failure during the onboard process will result in an an
    OnboardException. The exception includes a reason "slug" as defined below
    as well as a humanized message.
    """

    REASONS = (
        "fail-config",  # config provided is not valid
        "fail-connect",  # device is unreachable at IP:PORT
        "fail-execute",  # unable to execute device/API command
        "fail-login",  # bad username/password
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
    """
    Used to maintain information about the network device during the onboarding
    process.
    """

    def __init__(self, onboarding_task, username=None, password=None):
        """
        Initialize the network device keeper instance and ensure the required
        configuration parameters are provided.

        Parameters
        ----------
        config : dict - config params.

        Raises
        ------
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
        self.username = username or os.environ.get("NAPALM_USERNAME", None)
        self.password = password or os.environ.get("NAPALM_PASSWORD", None)

    def check_reachability(self):
        """
        Ensure that the device at the mgmt-ipaddr provided is reachable.  We do this
        check before attempting other "show" commands so that we know we've got a
        device that can be reached.

        Raises
        ------
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

    def get_required_info(self):
        """
        Gather information from the network device that is needed to onboard
        the device into the NetBox system.

        Raises
        ------
        OnboardException('fail-login'):
            When unable to login to device

        OnboardException('fail-exectute'):
            When unable to run commands to collect device information

        OnboardException('fail-general'):
            Any other unexpected device comms failure.
        """
        self.check_reachability()
        mgmt_ipaddr = self.ot.ip_address

        logging.info("COLLECT: device information %s", mgmt_ipaddr)

        try:
            driver_name = self.ot.platform.napalm_driver

            driver = get_network_driver(driver_name)
            dev = driver(hostname=mgmt_ipaddr, username=self.username, password=self.password, timeout=self.ot.timeout)

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

        try:
            mgmt_ifname, mgmt_pflen = first(
                (if_name, if_addr_data["prefix_length"])
                for if_name, if_data in ip_ifs.items()
                for if_addr, if_addr_data in if_data["ipv4"].items()
                if if_addr == mgmt_ipaddr
            )

        except Exception as exc:
            raise OnboardException(reason="fail-general", message=str(exc))

        # retain the attributes that will be later used by NetBox processing.

        self.hostname = facts["hostname"]
        self.vendor = facts["vendor"].title()
        self.model = facts["model"].lower()
        self.serial_number = facts["serial_number"]
        self.mgmt_ifname = mgmt_ifname
        self.mgmt_pflen = mgmt_pflen


# -----------------------------------------------------------------------------
#
#                            NetBox Device Keeper
#
# -----------------------------------------------------------------------------


class NetboxKeeper:
    """
    Used to manage the information relating to the network device within the
    NetBox server.
    """

    def __init__(self, netdev):
        """
        Creates an instance to the NetBox API and initializes the managed
        attributes that are used throughout the onboard processing.

        Parameters
        ----------
        netdev : NetdevKeeper - instance
        """
        self.netdev = netdev

        # these attributes are netbox model instances as discovered/created
        # through the course of processing.

        self.site = None
        self.platform = None
        self.manufacturer = None
        self.device_type = None
        self.device_role = None
        self.device = None
        self.interface = None
        self.primary_ip = None

    def ensure_device_type(self):
        """
        This function ensures that the Device Type (slug) exists in NetBox
        assocaited to the netdev "model" and  `vendor` (manufacturer).

        Raises
        ------
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
            self.manufacturer = Manufacturer.objects.get(name=self.netdev.vendor)
        except Manufacturer.DoesNotExist:
            raise OnboardException(reason="fail-config", message=f"ERROR manufacturer not found: {self.netdev.vendor}")

        # Now see if the device type (slug) already exists, and if so check to make
        # sure that it is not assigned as a different manufacturer

        slug = self.netdev.model
        if re.search(r"[^a-zA-Z0-9\-_]+", slug):
            logging.warning("device model is not sluggable: %s", slug)
            self.netdev.model = slug.replace(" ", "-")
            logging.warning("device model is now: %s", self.netdev.model)

        try:
            self.device_type = DeviceType.objects.get(slug=self.netdev.model)
        except DeviceType.DoesNotExist:
            logging.info("device-type does not exist yet")

        if self.device_type:
            if self.device_type.manufacturer.id == self.manufacturer.id:
                logging.info("EXISTS: device-type: %s", self.netdev.model)
                return

            raise OnboardException(
                reason="fail-config",
                message=f"ERROR device type {self.netdev.model}" f"already exists for vendor {self.netdev.vendor}",
            )

        # At this point create and return the new netbox device-type instance.from
        logging.info("CREATE: device-type: %s", self.netdev.model)

        self.device_type = DeviceType.objects.create(
            slug=self.netdev.model, model=self.netdev.model.upper(), manufacturer=self.manufacturer
        )

        self.device_type.save()

    def ensure_device_instance(self):
        """
        Ensure that the device instance exists in NetBox and is assigned either
        the provide device role, or uses the DEFAULT_ROLE value.
        """

        self.device, _ = Device.objects.get_or_create(
            name=self.netdev.hostname,
            device_type=self.device_type,
            device_role=self.netdev.ot.role,
            platform=self.netdev.ot.platform,
            site=self.netdev.ot.site,
        )

        self.device.serial = self.netdev.serial_number
        self.device.save()

    def ensure_interface(self):
        """
        Ensures that the interface associated with the mgmt_ipaddr exists and
        is assigned to the device.
        """

        self.interface, _ = Interface.objects.get_or_create(name=self.netdev.mgmt_ifname, device=self.device)

    def ensure_primary_ip(self):
        """
        Ensure that the network device mgmt_ipaddr exists in IPAM, is assigned
        to the device interface, and is also assigned as the device primary IP
        address.
        """
        mgmt_ipaddr = self.netdev.ot.ip_address

        # see if the primary IP address exists in IPAM
        self.primary_ip, created = IPAddress.objects.get_or_create(
            address=f"{mgmt_ipaddr}/{self.netdev.mgmt_pflen}", family=4
        )

        if created or not self.primary_ip.interface:
            logging.info("ASSIGN: IP address %s to %s", self.primary_ip.address, self.interface.name)
            self.primary_ip.interface = self.interface

        self.primary_ip.save()

        # Ensure the primary IP is assigned to the device
        self.device.primary_ip4 = self.primary_ip
        self.device.save()

    def ensure_device(self):
        """
        Ensure that the device represented by the dev_info data exists in the NetBox
        system.  This means the following is true:

            1. The device 'hostname' exists and is a member of 'site'
            2. The 'serial_number' is assigned to the device
            3. The 'model' is an existing DevType and assigned to the device.
            4. The 'mgmt_ifname' exists as an interface of the device
            5. The 'mgmt_ipaddr' is assigned to the mgmt_ifname
            6. The 'mgmt_ipaddr' is assigned as the primary IP address to the device.

        If the device previously exists and is not a member of the give site, then raise
        an OnboardException.

        """

        self.ensure_device_type()
        self.ensure_device_instance()
        self.ensure_interface()
        self.ensure_primary_ip()
