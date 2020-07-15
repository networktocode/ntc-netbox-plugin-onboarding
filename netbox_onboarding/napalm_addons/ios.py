"""Class built for the IOS device Extensions."""
# Load Genie Libraries
from genie.conf.base import Device
from genie.libs.parser.utils import get_parser
from pyats.datastructures import AttrDict

# Load onboarding exception
from netbox_onboarding.onboard import OnboardException


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

    def parse_stack_commands(self):
        """Method to parse the output and determine if there are multiple devices.
        
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
        device_os = "ios"
        command = "show version"
        # Create Genie Device Object
        genie_device = Device("new_device", os=device_os)
        genie_device.custom.setdefault("abstraction", {})
        genie_device.custom["abstraction"]["order"] = ["os"]
        genie_device.cli = AttrDict({"execute": None})

        try:
            # Get the parser for the genie object
            get_parser(command, genie_device)

            # Optionally store the parsed_show_version
            self.parsed_show_version = genie_device.parse(command, output=self.show_version)

            # Return the device_dict
            return self.parsed_show_version.get("version", {}).get("switch_num", {})
        except:
            raise OnboardException("fail-genie", f"Failed to use Genie Parser to get structured data.")
