# Frequently Asked Questions

## Is it possible to disable the automatic creation of Device Type, Device Role or Platform ?

> **Yes**, Using the plugin settings, it's possible to control individually the creation of `device_role`, `device_type`, `manufacturer` & `platform`

```
# configuration.py
# If need you can override the default settings
# PLUGINS_CONFIG = {
#   "netbox_onboarding": {
#         "create_platform_if_missing": True,
#         "create_manufacturer_if_missing": True,
#         "create_device_type_if_missing": True,
#         "create_device_role_if_missing": True,
#         "default_device_role": "network",
#   }
# }
```

## How can I update the default credentials used to connect to a device ?

> By default, the plugin is using the credentials defined in the main `configuration.py` for Napalm (`NAPALM_USERNAME`/`NAPALM_PASSWORD`). You can update the default credentials in `configuration.py` or you can provide specific one for each onboarding task.

## Does this plugin support the discovery and the creation of all interfaces and IP Addresses ?

> **No**, The plugin will only discover and create the management interface and the management IP address. Importing all interfaces and IP addresses is a much larger problem that requires more preparation. This is out of scope of this project.

## Does this plugin support the discovery of device based on fqdn ? 

> **No**, Current the onbarding process is based on an IP address, please open an issue to discuss your use case if you would like to see support for FQDN based devices too. 

## Does this plugin support the discovery of Stack or Virtual Chassis devices ?

> **Partially**, Multi member devices (Stack, Virtual Chassis, FW Pair) can be imported but they will be created as a single device. 

## Is this plugin able to automatically discover the type of my device ? 

> **Yes**, The plugin is leveraging [Netmiko](https://github.com/ktbyers/netmiko) & [Napalm](https://napalm.readthedocs.io/en/latest/) to attempt to automatically discover the OS and the model of each device.

## How many device can I import at the same time ?

> **Many**, There are no strict limitations regarding the number of devices that can be imported. The speed at which devices will be imported will depend of the number of active RQ workers.

## Do I need to setup a dedicated RQ Worker node ?

> **No**, The plugin is leveraging the existing RQ Worker infrastructure already in place in NetBox, the only requirement is to ensure the plugin itself is installed in the Worker node.

## Why don't I see a webhook generated when a new device is onboarded successfully ?

> It's expected that any changes done asynchronously in NetBox currently (within a worker) will not generate a webhook.


