from ntc-netbox-plugin-onboarding.onboarding.onboarding import StandaloneOnboarding

class OnboardingDriverExtensions(object):
    def __init__(self, napalm_device):
        self.napalm_device = napalm_device

    def get_onboarding_class(self):
        """
        Return onboarding class for IOS driver
        Currently supported is Standalone Onboarding Process
        """
        return StandaloneOnboarding

    def get_ext_result(self):
        return None
