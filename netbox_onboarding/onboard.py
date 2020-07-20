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

from .netdev_keeper import NetdevKeeper

__all__ = []

PLUGIN_SETTINGS = settings.PLUGINS_CONFIG["netbox_onboarding"]


class OnboardingTaskManager(object):
    def __init__(self, ot):
        self.ot = ot

    @property
    def napalm_driver(self):
        if self.ot.platform and self.ot.platform_napalm_driver:
            return self.ot.platform.napalm_driver
        else:
            return None

    @property
    def hostname(self):
        return self.ot.hostname

    @property
    def port(self):
        return self.ot.port

    @property
    def timeout(self):
        return self.ot.timeout

    @property
    def nb_task_info(self):
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

        # Create instance of Onboarding Task Manager class:
        otm = OnboardingTaskManager(ot)

        netdev = NetdevKeeper(hostname=otm.hostname,
                              port=otm.port,
                              timeout=otm.timeout,
                              username=self.username,
                              password=self.password,
                              secret=self.secret,
                              napalm_driver=otm.napalm_driver,
                              )

        netdev.get_required_info()

        netdev_info = netdev.get_netdev_dict()

        nb_keeper_kwargs = {
            **netdev_info,
            **otm.nb_task_info
        }

        onboarding_cls = netdev_info['onboarding_class']()
        onboarding_cls.run(nb_keeper_kwargs=nb_keeper_kwargs)

        self.created_device = onboarding.created_device
