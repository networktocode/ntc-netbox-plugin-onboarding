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
import socket

import netaddr
from django.conf import settings
from napalm import get_network_driver
from napalm.base.exceptions import ConnectionException, CommandErrorException
from netaddr.core import AddrFormatError
from netmiko.ssh_autodetect import SSHDetect
from netmiko.ssh_exception import NetMikoAuthenticationException
from netmiko.ssh_exception import NetMikoTimeoutException
from paramiko.ssh_exception import SSHException

from .constants import NETMIKO_TO_NAPALM

__all__ = []

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["netbox_onboarding"]


# locate the interface assigned with the self.hostname value and retain
# the interface name and IP prefix-length so that we can use it
# when creating the IPAM IP-Address instance.
# Note that in some cases (e.g., NAT) the hostname may differ than
# the interface addresses present on the device. We need to handle this.
def get_mgmt_info(hostname, ip_ifs):
    """Get the interface name and prefix length for the management interface."""
    for if_name, if_data in ip_ifs.items():
        for if_addr, if_addr_data in if_data["ipv4"].items():
            if if_addr == hostname:
                return (if_name, if_addr_data["prefix_length"])

    return (default_mgmt_if, default_mgmt_pfxlen)


class NetdevKeeper:
    """Used to maintain information about the network device during the onboarding process."""

    def __init__(self, hostname, port=None, timeout=None, username=None, password=None, secret=None,
                 napalm_driver=None):
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
        # self.ot = onboarding_task

        # Attributes that are set when reading info from device

        # Inputs
        self.hostname = hostname
        self.port = port
        self.timeout = timeout
        self.username = username or settings.NAPALM_USERNAME
        self.password = password or settings.NAPALM_PASSWORD
        self.secret = secret or settings.NAPALM_ARGS.get("secret", None)
        self.napalm_driver = napalm_driver

        # Outputs
        self.netdev_vendor = None
        self.netdev_model = None
        self.netdev_serial_number = None
        self.netdev_mgmt_ifname = None
        self.netdev_mgmt_pflen = None
        self.netmiko_device_type = None

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
            checked_ip = netaddr.IPAddress(self.hostname)
            return True
        # Catch when someone has put in a prefix address, raise an exception
        except ValueError:
            raise OnboardException(
                reason="fail-general", message=f"ERROR appears a prefix was entered: {self.hostname}"
            )
        # An AddrFormatError exception means that there is not an IP address in the field, and should continue on
        except AddrFormatError:
            try:
                # Do a lookup of name to get the IP address to connect to
                checked_ip = socket.gethostbyname(self.hostname)
                self.hostname = checked_ip
                return True
            except socket.gaierror:
                # DNS Lookup has failed, Raise an exception for unable to complete DNS lookup
                raise OnboardException(
                    reason="fail-dns", message=f"ERROR failed to complete DNS lookup: {self.hostname}"
                )

    def check_reachability(self):
        """Ensure that the device at the mgmt-ipaddr provided is reachable.

        We do this check before attempting other "show" commands so that we know we've got a
        device that can be reached.

        Raises:
          OnboardException('fail-connect'):
            When device unreachable
        """

        logging.info("CHECK: IP %s:%s", self.hostname, self.port)

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((self.hostname, self.port))

        except (socket.error, socket.timeout, ConnectionError):
            raise OnboardException(reason="fail-connect",
                                   message=f"ERROR device unreachable: {self.hostname}:{self.port}")

    def guess_netmiko_device_type(self):
        """Guess the device type of host, based on Netmiko."""
        guessed_device_type = None

        remote_device = {
            "device_type": "autodetect",
            "host": self.hostname
            "username": self.username,
            "password": self.password,
            "secret": self.secret,
        }

        try:
            logging.info("INFO guessing device type: %s", kwargs.get("host"))
            guesser = SSHDetect(**remote_device)
            guessed_device_type = guesser.autodetect()
            logging.info("INFO guessed device type: %s", guessed_device_type)

        except NetMikoAuthenticationException as err:
            logging.error("ERROR %s", err)
            raise OnboardException(reason="fail-login",
                                   message="ERROR {}".format(str(err))
                                   )

        except (NetMikoTimeoutException, SSHException) as err:
            logging.error("ERROR %s", err)
            raise OnboardException(reason="fail-connect",
                                   message="ERROR {}".format(str(err))
                                   )

        except Exception as err:
            logging.error("ERROR %s", err)
            raise OnboardException(reason="fail-general",
                                   message="ERROR {}".format(str(err)))

        logging.info("INFO device type is %s", guessed_device_type)

        return guessed_device_type

    def set_napalm_driver_name(self):
        if not self.napalm_driver:
            netmiko_device_type = self.guess_netmiko_device_type()
            logging.info(f"Guessed Netmiko Device Type: {netmiko_device_type}")

            self.netmiko_device_type = guessed_device_type
            self.napalm_driver = NETMIKO_TO_NAPALM.get(netmiko_device_type)

    def check_napalm_driver_name(self):
        if not self.napalm_driver:
            raise OnboardException(
                reason="fail-general",
                message=f"Onboarding for Platform {platform_slug} not "
                        f"supported, as it has no specified NAPALM driver",
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

        logging.info("COLLECT: device information %s", self.hostname)

        try:
            # Get Napalm Driver with Netmiko if needed
            self.set_napalm_driver_name()

            # Raise if no Napalm Driver not selected
            self.check_napalm_driver_name()

            driver = get_network_driver(self.napalm_driver)
            optional_args = settings.NAPALM_ARGS.copy()
            optional_args["secret"] = self.secret

            dev = driver(
                hostname=self.hostname,
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

            # retain the attributes that will be later used by NetBox processing.
            self.netdev_hostname = facts["hostname"]
            self.netdev_vendor = facts["vendor"].title()
            self.netdev_model = facts["model"].lower()
            self.netdev_serial_number = facts["serial_number"]
            self.netdev_mgmt_ifname, self.netdev_mgmt_pflen = get_mgmt_info(
                hostname=self.hostname,
                ip_ifs=ip_ifs
            )

        except ConnectionException as exc:
            raise OnboardException(reason="fail-login", message=exc.args[0])

        except CommandErrorException as exc:
            raise OnboardException(reason="fail-execute", message=exc.args[0])

        except Exception as exc:
            raise OnboardException(reason="fail-general", message=str(exc))

    def get_netdev_dict(self):
        netdev_dict = {
            'netdev_hostname': self.netdev_hostname,
            'netdev_vendor': self.netdev_vendor,
            'netdev_model': self.netdev_model,
            'netdev_serial_number': self.netdev_serial_number,
            'netdev_mgmt_ifname': self.netdev_mgmt_ifname,
            'netdev_mgmt_pflen': self.netdev_mgmt_pflen,
            'netdev_netmiko_device_type': self.netmiko_device_type,
        }

        return netdev_dict
