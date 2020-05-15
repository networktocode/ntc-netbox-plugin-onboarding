

# Frequenty Asked Questions

### Is it possible to disable the automatic creation of Device Type or Device Role ?

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

### Does this plugin support the discovery and the creation of Interfaces and IP Address

> **No**, this plugin will only discover and create the management interface and the management IP address. Importing all interfaces and IP addresses is a much larger problem that requires more preparation. This is out of scope of this project.

### Does this plugin support the discovery of Stack or Virtual Chassis devices

> **Partially**, Multi member devices (Stack, Virtual Chassis, FW Pair) can be imported but they will be seen as a single device. 

### Is this plugin able to automatically discover the type of my device

> **Yes**, This plugin is leveraging Netmiko & Napalm to attempt to automatically discover the type of OS of each device.

### How many device can I import at the same time

> **Many**, There is really not strict limitations regarding the number of devices that can be importer at the same time. The speed at which devices will be imported will depend of the number of active RQ workers.

### Do I need to setup a dedicated RQ Worker node ?

> **No**, The plugin is leveraging the existing RQ Worker infrastructure already in place in NetBox, the only requirements is to ensure the plugin it self is installed in the Worker node itself.


