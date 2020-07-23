"""Class built for the IOS device Extensions."""
# Load TextFSM Parsing Library
from ntc_templates.parse import parse_output

# Load onboarding exception
from netbox_onboarding.onboard import OnboardException
from netbox_onboarding.onboarding.onboarding import StandaloneOnboarding, CiscoStackOnboarding


class OnboardingDriverExtensions:
    """NAPALM device extensions."""

    def __init__(self, napalm_device):
        self.driver_addon_result = {}
        self.napalm_device = napalm_device
        self.onboarding_class = None
        self.get_onboarding_class()

    def get_onboarding_class(self):
        """Method to get the onboarding class type.
        
        Method will determine what type of onboarding class is to be used and assign it to
        self.onboarding_class.

        Returns:
            (Onboarding Class): Onboarding class to be used
        """
        self._get_stack_commands_output()
        self._parse_with_textfsm()
        if len(self.driver_addon_result['device_list']) <= 1:
            return StandaloneOnboarding
        else:
            return CiscoStackOnboarding


    def _get_stack_commands_output(self):
        """Method to execute command(s) to get necessary info to determine the number of devices in a stack.
        
        This method is where you get the outputs as necessary to support gathering of the size of the stack, including
        serial numbers and model numbers of each unit.
        """
        # Set command to run `show version` in order to get information about the device
        command = "show version"

        # Run the command against the device
        cli_output = self.napalm_device.cli([command])
        self.driver_addon_result["show_version"] = cli_output[command]

    def _parse_with_textfsm(self):
        """Method to parse the output with TextFSM to get the information about the devices

        This method is where all of the logic should be stored to get the devices. Returned items should be in the
        format of a dictionary:

        [
            {
                "position": position,
                "serial_number": sn,
                "model": model
            },
            {
                "position": position,
                "serial_number": sn,
                "model": model
            }
        ]

        {
            "1": {
                "serial_number": "<info>",
                "model": "<info>",
                ...
            },
            "2": {
                "serial_number": "<info>",
                "model": "<info>",
                ...
            },
            "4": {
                "serial_number": "<info>",
                "model": "<info>",
                ...
            }
        }

        Store the list of devices in an object named `self.device_dict`. Each unit number should be the top key in the
        dictionary. This is what will be in the device name after the delination character such as demo_swt01:4.
        """
        device_list = []
        
        # Onboarding of the IOSv device needs to be only from NAPALM getters
        if "IOSv" not in self.driver_addon_result['show_version']:
            version_parsed = parse_output(
                platform="cisco_ios", command="show version", data=self.driver_addon_result['show_version'])
            for loop_control in range(0, len(version_parsed[0]["serial"])):
                device_list.append(
                    {
                        "position": loop_control + 1,
                        "serial_number": version_parsed[0]["serial"][loop_control],
                        "model": version_parsed[0]["hardware"][loop_control],
                        "mac_address": version_parsed[0]["mac"][loop_control]
                    }
                )

        self.driver_addon_result["device_list"] = device_list
