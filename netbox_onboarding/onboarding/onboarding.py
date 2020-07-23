from netbox_onboarding.netbox_keeper import NetboxKeeper


class Onboarding(object):
    def __init__(self):
        self.created_device = None


class StandaloneOnboarding(Onboarding):
    def run(self, onboarding_kwargs):
        nb = NetboxKeeper(**onboarding_kwargs)
        nb.ensure_device()
        self.created_device = nb.device

class CiscoStackOnboarding(Onboarding):
    pass
#     def run(self):
#         def _stack_hostname(slot_number):
#             return self.netdev.hostname if slot_number == 1 else "{}-{}".format(self.netdev.hostname, slot_number)
#
#         def _stack_mgmt_ifname(slot_number):
#             return self.netdev.mgmt_ifname if slot_number == 1 else None
#
#         def _stack_mgmt_pflen(slot_number):
#             return self.netdev.mgmt_pflen if slot_number == 1 else None
#
#         primary_device = None
#
#         # Abstract network devices and create NetdevKeeper object per stack member
#         with transaction.atomic():
#             _ot_ip = self.ot.ip_address
#             for stack_member in self.netdev.multi_device_structured_inventory:
#
#                 stack_netdev = OfflineNetdevKeeper()
#                 stack_netdev.ot = self.ot
#
#                 # Don't let children devices to inherit IP address
#                 # Stack members are identified in Device object by name first
#                 # Stack masters are lookup by IP address first
#                 if stack_member['position'] > 1:
#                     stack_netdev.ot.ip_address = ''
#
#                 stack_netdev.hostname = _stack_hostname(slot_number=stack_member['position'])
#                 stack_netdev.vendor = self.netdev.vendor
#                 stack_netdev.model = stack_member['model']
#                 stack_netdev.platform = self.netdev.platform
#                 stack_netdev.serial = stack_member['serial']
#                 stack_netdev.deployment_mode = self.netdev.deployment_mode
#                 stack_netdev.mgmt_ifname = _stack_mgmt_ifname(slot_number=stack_member['position'])
#                 stack_netdev.mgmt_pflen = _stack_mgmt_pflen(slot_number=stack_member['position'])
#                 stack_netdev.inventory = self.netdev.inventory if stack_member['position'] == 1 else None
#
#                 nb = NetboxKeeper(netdev=stack_netdev)
#                 nb.ensure_device()
#
#                 # Create virtual chassis for first member
#                 # List is already verified to be sorted and containing the slot number 1
#                 if stack_member['position'] == 1:
#                     #
#                     # TODO:
#                     #  - virtual chassis mod instread of recr
#                     #
#                     nb.recreate_virtual_chassis()
#                     vc = nb.virtual_chassis
#                     primary_device = nb.device
#
#                 # Update virtual chassis and vc position information for every stack member
#                 # including master
#                 nb.device.virtual_chassis = vc
#                 nb.device.vc_position = stack_member['position']
#                 nb.device.save()
#
#             self.ot.ip_address = _ot_ip
#
#         # Set back the created device one transaction is committed
#         self.created_device = primary_device
