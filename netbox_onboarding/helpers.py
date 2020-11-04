"""OnboardingTask Django model.

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

import socket

import netaddr
from netaddr.core import AddrFormatError

from .exceptions import OnboardException


def onboarding_task_fqdn_to_ip(ot):
    """Method to assure OT has FQDN resolved to IP address and rewritten into OT.

    If it is a DNS name, attempt to resolve the DNS address and assign the IP address to the
    name.

    Returns:
        None

    Raises:
      OnboardException("fail-general"):
        When a prefix was entered for an IP address
      OnboardException("fail-dns"):
        When a Name lookup via DNS fails to resolve an IP address
    """
    try:
        # If successful, this is an IP address and can pass
        netaddr.IPAddress(ot.ip_address)
    # Raise an Exception for Prefix values
    except ValueError:
        raise OnboardException(reason="fail-general", message=f"ERROR appears a prefix was entered: {ot.ip_address}")
    # An AddrFormatError exception means that there is not an IP address in the field, and should continue on
    except AddrFormatError:
        try:
            # Perform DNS Lookup
            ot.ip_address = socket.gethostbyname(ot.ip_address)
            ot.save()
        except socket.gaierror:
            # DNS Lookup has failed, Raise an exception for unable to complete DNS lookup
            raise OnboardException(reason="fail-dns", message=f"ERROR failed to complete DNS lookup: {ot.ip_address}")
