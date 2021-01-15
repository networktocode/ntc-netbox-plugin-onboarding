"""Onboard.

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

from .netdev_keeper import NetdevKeeper

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["netbox_onboarding"]


class OnboardingTaskManager:
    """Onboarding Task Manager."""

    def __init__(self, ot):
        """Inits class."""
        self.ot = ot

    @property
    def napalm_driver(self):
        """Return napalm driver name."""
        if self.ot.platform and self.ot.platform.napalm_driver:
            return self.ot.platform.napalm_driver

        return None

    @property
    def optional_args(self):
        """Return platform optional args."""
        if self.ot.platform and self.ot.platform.napalm_args:
            return self.ot.platform.napalm_args

        return {}

    @property
    def ip_address(self):
        """Return ot's ip address."""
        return self.ot.ip_address

    @property
    def port(self):
        """Return ot's port."""
        return self.ot.port

    @property
    def timeout(self):
        """Return ot's timeout."""
        return self.ot.timeout

    @property
    def site(self):
        """Return ot's site."""
        return self.ot.site

    @property
    def device_type(self):
        """Return ot's device type."""
        return self.ot.device_type

    @property
    def role(self):
        """Return it's device role."""
        return self.ot.role

    @property
    def platform(self):
        """Return ot's device platform."""
        return self.ot.platform


class OnboardingManager:
    """Onboarding Manager."""

    def __init__(self, ot, username, password, secret):
        """Inits class."""
        # Create instance of Onboarding Task Manager class:
        otm = OnboardingTaskManager(ot)

        self.username = username or settings.NAPALM_USERNAME
        self.password = password or settings.NAPALM_PASSWORD
        self.secret = secret or otm.optional_args.get("secret", None) or settings.NAPALM_ARGS.get("secret", None)

        netdev = NetdevKeeper(
            hostname=otm.ip_address,
            port=otm.port,
            timeout=otm.timeout,
            username=self.username,
            password=self.password,
            secret=self.secret,
            napalm_driver=otm.napalm_driver,
            optional_args=otm.optional_args or settings.NAPALM_ARGS,
        )

        netdev.get_onboarding_facts()
        netdev_dict = netdev.get_netdev_dict()

        onboarding_kwargs = {
            # Kwargs extracted from OnboardingTask:
            "netdev_mgmt_ip_address": otm.ip_address,
            "netdev_nb_site_slug": otm.site.slug if otm.site else None,
            "netdev_nb_device_type_slug": otm.device_type,
            "netdev_nb_role_slug": otm.role.slug if otm.role else PLUGIN_SETTINGS["default_device_role"],
            "netdev_nb_role_color": PLUGIN_SETTINGS["default_device_role_color"],
            "netdev_nb_platform_slug": otm.platform.slug if otm.platform else None,
            # Kwargs discovered on the Onboarded Device:
            "netdev_hostname": netdev_dict["netdev_hostname"],
            "netdev_vendor": netdev_dict["netdev_vendor"],
            "netdev_model": netdev_dict["netdev_model"],
            "netdev_serial_number": netdev_dict["netdev_serial_number"],
            "netdev_mgmt_ifname": netdev_dict["netdev_mgmt_ifname"],
            "netdev_mgmt_pflen": netdev_dict["netdev_mgmt_pflen"],
            "netdev_netmiko_device_type": netdev_dict["netdev_netmiko_device_type"],
            "onboarding_class": netdev_dict["onboarding_class"],
            "driver_addon_result": netdev_dict["driver_addon_result"],
        }

        onboarding_cls = netdev_dict["onboarding_class"]()
        onboarding_cls.credentials = {"username": self.username, "password": self.password, "secret": self.secret}
        onboarding_cls.run(onboarding_kwargs=onboarding_kwargs)

        self.created_device = onboarding_cls.created_device
