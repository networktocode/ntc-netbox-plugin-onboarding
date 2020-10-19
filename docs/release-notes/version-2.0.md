# ntc-netbox-plugin-onboarding v2.0 Release Notes

## v2.0

### Enhancements

* NetBox 2.9 support - Supported releases 2.8 and 2.9
* Onboarding extensions - Customizable onboarding process through Python modules.
* Onboarding details exposed in a device view - Date, Status, Last success and Latest task id related to the onboarded device are presented under the device view.
* Onboarding task view - Onboarding details exposed in a dedicated view, including NetBox's ChangeLog.
* Onboarding Changelog - Onboarding uses NetBox's ChangeLog to display user and changes made to the Onboarding Task object.
* Skip onboarding feature - New attribute in the OnboardingDevice model allows to skip the onboarding request on devices with disabled onboarding setting.

### Bug Fixes

* Fixed race condition in `worker.py`
* Improved logging

### Additional Changes

* Platform map now includes NAPALM drivers as defined in NetBox
* Tests have been refactored to inherit NetBox's tests
* Onboarding process will update the Device found by the IP-address lookup. In case of no existing device with onboarded IP-address is found in NetBox, onboarding might update the existing NetBox' looking up by network device's hostname.
* Onboarding will raise Exception when `create_device_type_if_missing` is set to `False` for existing Device with DeviceType mismatch (behaviour pre https://github.com/networktocode/ntc-netbox-plugin-onboarding/issues/74)
