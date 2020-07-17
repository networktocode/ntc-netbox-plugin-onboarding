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

from django.conf import settings

__all__ = []

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["netbox_onboarding"]


class OnboardingTaskManager(object):
    @staticmethod
    def get_task_info(ot):
        task_info = {
            'netdev_mgmt_ip_address': ot.ip_address,
            'netdev_nb_device_type_slug': ot.device_type,
            'netdev_nb_role_slug': ot.role.slug if ot.role else None,
            'netdev_nb_site_slug': ot.site.slug if ot.site else None,
            'netdev_nb_platform_slug': ot.platform.slug if ot.platform else None,
        }

        return task_info


class OnboardingManager(object):
    def __init__(self, ot, username, password, secret):
        self.username = username
        self.password = password
        self.secret = secret

        netdev = NetdevKeeper(ot,
                              username=self.username,
                              password=self.password,
                              secret=self.secret
                              )

        netdev.get_required_info()

        netdev_info = netdev.get_netdev_dict()
        task_info = OnboardingTaskManager.get_task_info(ot)

        nb_keeper_kwargs = {
            **netdev_info,
            **task_info
        }

        onboarding = globals()[self.netdev.deployment_mode.cls]()
        onboarding.run(nb_keeper_kwargs=nb_keeper_kwargs)

        self.created_device = onboarding.created_device


class Onboarding(object):
    def __init__(self):
        self.created_device = None


class StandaloneOnboarding(Onboarding):
    def run(self, nb_keeper_kwargs):
        nb = NetboxKeeper(**kwargs)
        nb.ensure_device()
        self.created_device = nb.device


class StackOnboarding(Onboarding):
    def run(self):
        def _stack_hostname(slot_number):
            return self.netdev.hostname if slot_number == 1 else "{}-{}".format(self.netdev.hostname, slot_number)

        def _stack_mgmt_ifname(slot_number):
            return self.netdev.mgmt_ifname if slot_number == 1 else None

        def _stack_mgmt_pflen(slot_number):
            return self.netdev.mgmt_pflen if slot_number == 1 else None

        primary_device = None

        # Abstract network devices and create NetdevKeeper object per stack member
        with transaction.atomic():
            _ot_ip = self.ot.ip_address
            for stack_member in self.netdev.multi_device_structured_inventory:

                stack_netdev = OfflineNetdevKeeper()
                stack_netdev.ot = self.ot

                # Don't let children devices to inherit IP address
                # Stack members are identified in Device object by name first
                # Stack masters are lookup by IP address first
                if stack_member['position'] > 1:
                    stack_netdev.ot.ip_address = ''

                stack_netdev.hostname = _stack_hostname(slot_number=stack_member['position'])
                stack_netdev.vendor = self.netdev.vendor
                stack_netdev.model = stack_member['model']
                stack_netdev.platform = self.netdev.platform
                stack_netdev.serial = stack_member['serial']
                stack_netdev.deployment_mode = self.netdev.deployment_mode
                stack_netdev.mgmt_ifname = _stack_mgmt_ifname(slot_number=stack_member['position'])
                stack_netdev.mgmt_pflen = _stack_mgmt_pflen(slot_number=stack_member['position'])
                stack_netdev.inventory = self.netdev.inventory if stack_member['position'] == 1 else None

                nb = NetboxKeeper(netdev=stack_netdev)
                nb.ensure_device()

                # Create virtual chassis for first member
                # List is already verified to be sorted and containing the slot number 1
                if stack_member['position'] == 1:
                    #
                    # TODO:
                    #  - virtual chassis mod instread of recr
                    #
                    nb.recreate_virtual_chassis()
                    vc = nb.virtual_chassis
                    primary_device = nb.device

                # Update virtual chassis and vc position information for every stack member
                # including master
                nb.device.virtual_chassis = vc
                nb.device.vc_position = stack_member['position']
                nb.device.save()

            self.ot.ip_address = _ot_ip

        # Set back the created device one transaction is committed
        self.created_device = primary_device
