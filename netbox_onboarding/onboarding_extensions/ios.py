from ntc_netbox_plugin_onboarding.onboarding.onboarding import StandaloneOnboarding


class OnboardingDriverExtensions(object):
    def __init__(self, napalm_device):
        self.napalm_device = napalm_device

    def get_onboarding_class(self):
        """
        Return onboarding class for IOS driver
        Currently supported is Standalone Onboarding Process

        Result of this method is used by the OnboardingManager to
        initiate the instance of the onboarding class.
        """
        return StandaloneOnboarding

    def get_ext_result(self):
        """
        This method is used to store any object as a return value.
        Result of this method is passed to the onboarding class as
        driver_addon_result argument.

        :return: Any()
        """
        return None
