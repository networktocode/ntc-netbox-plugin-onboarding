"""Class built for the IOS device Extensions."""
# Load TextFSM Parsing Library
from ntc_templates.parse import parse_output

# Load onboarding exception
from netbox_onboarding.onboard import OnboardException
from .helpers import GeneralDeploymentMode


class DeploymentMode(GeneralDeploymentMode):
    """ Driver Specific Deployment Mode Class """
    UNKNOWN = (0, None)
    STANDALONE = (1, "StandaloneOnboarding")
    CISCO_IOS_STACK = (100, "StackOnboarding")
    CISCO_IOS_VSS = (200, "VssOnboarding")


class NapalmDeviceExtensions:
    """NAPALM device extensions."""

    def __init__(self, napalm_device):
        self.device_dict: dict = {}
        self.napalm_device = napalm_device
        self.show_version: str = ""
        self.parsed_show_version: dict = {}

    def get_stack_commands_output(self):
        """Method to execute command(s) to get necessary info to determine the number of devices in a stack.
        
        This method is where you get the outputs as necessary to support gathering of the size of the stack, including
        serial numbers and model numbers of each unit.
        """
        # Set command to run `show version` in order to get information about the device
        command = "show version"

        # Run the command against the device
        cli_output = self.napalm_device.cli([command])
        raw_output = cli_output[command]
        self.show_version = raw_output

    def parse_with_textfsm(self):
        """Method to parse the output with TextFSM to get the information about the devices

        This method is where all of the logic should be stored to get the devices. Returned items should be in the
        format of a dictionary:

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
        return_dict = {}
        # Onboarding of the IOSv device needs to be only from NAPALM getters
        if "IOSv" in self.show_version:
            return {}
        version_parsed = parse_output(platform="cisco_ios", command="show version", data=self.show_version)
        for loop_control in range(0, len(version_parsed[0]["serial"])):
            return_dict[str(loop_control + 1)] = {
                "serial_number": version_parsed[0]["serial"][loop_control],
                "model": version_parsed[0]["hardware"][loop_control],
                "mac_address": version_parsed[0]["mac"][loop_control]
            }

        return return_dict
