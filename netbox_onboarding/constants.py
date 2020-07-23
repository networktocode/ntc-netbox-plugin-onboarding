"""Constants for netbox_onboarding plugin."""

from dcim.models import Platform

NETMIKO_TO_NAPALM_STATIC = {
    "cisco_ios": "ios",
    "cisco_nxos": "nxos_ssh",
    "arista_eos": "eos",
    "juniper_junos": "junos",
    "cisco_xr": "iosxr",
}

PLATFORM_TO_NAPALM_NETBOX = {platform.slug: platform.napalm_driver for platform in Platform.objects.all() if
                             platform.napalm_driver}

# Update Constants if Napalm driver is defined for NetBox Platform
NETMIKO_TO_NAPALM = {
    **NETMIKO_TO_NAPALM_STATIC,
    **PLATFORM_TO_NAPALM_NETBOX,
}
