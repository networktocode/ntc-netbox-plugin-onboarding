# NetBox Onboarding plugin

<!-- Build status with linky to the builds for ease of access. -->
[![Build Status](https://travis-ci.com/networktocode/ntc-netbox-plugin-onboarding.svg?token=29s5AiDXdkDPwzSmDpxg&branch=master)](https://travis-ci.com/networktocode/ntc-netbox-plugin-onboarding)

A plugin for [NetBox](https://github.com/netbox-community/netbox) to easily onboard new devices.

`ntc-netbox-plugin-onboarding` is using [Netmiko](https://github.com/ktbyers/netmiko), [NAPALM](https://napalm.readthedocs.io/en/latest/) & [Django-RQ](https://github.com/rq/django-rq) to simplify the onboarding process of a new device into NetBox down to an IP Address and a site.
The goal of this plugin is not to import everything about a device into NetBox but rather to help build quickly an inventory in NetBox that is often the first step into an automation journey.

## Installation

The plugin is available as a Python package in pypi and can be installed with pip
```shell
pip install ntc-netbox-plugin-onboarding
```

Once installed, the plugin needs to be enabled in your `configuration.py`
```python
# In your configuration.py
PLUGINS = ["netbox_onboarding"]

# PLUGINS_CONFIG = {
#   "netbox_onboarding": {
#     ADD YOUR SETTINGS HERE
#   }
# }
```

The plugin behavior can be controlled with the following list of settings

- `create_platform_if_missing` boolean (default True), If True, a new platform object will be created if the platform discovered by netmiko do not already exist and is in the list of supported platforms (`cisco_ios`, `cisco_nxos`, `arista_eos`, `juniper_junos`, `cisco_xr`)
- `create_device_type_if_missing` boolean (default True), If True, a new device type object will be created if the model discovered by Napalm do not match an existing device type.
- `create_manufacturer_if_missing` boolean (default True), If True, a new manufacturer object will be created if the manufacturer discovered by Napalm is do not match an existing manufacturer, this option is only valid if `create_device_type_if_missing` is True as well.
- `create_device_role_if_missing` boolean (default True), If True, a new device role object will be created if the device role provided was not provided as part of the onboarding and if the `default_device_role` do not already exist. 
- `default_device_role` string  (default "network")

## Usage
### Preparation

To work properly the plugin needs to know the Site, Platform, Device Type, Device Role of each device as well as its primary IP address.
It's recommended to create these objects in NetBox ahead of time and to provide them when you want to start the onboarding process.

If `Platform`, `Device Type` and/or `Device Role` are not provided, the plugin will try to identify these information automatically and, based on the settings, it can create them in NetBox as needed.
> If the Platform is provided, it must contains a valid Napalm driver available to the worker in Python

### Onboard a new device

A new device can be onboarded via :
- A web form  `/plugins/onboarding/add/`
- A CSV form to import multiple devices in bulk. `/plugins/onboarding/import/`
- An API, `POST /api/plugins​/onboarding​/onboarding​/`

During a successful onboarding process, a new device will be created in NetBox with its management interface and its primary IP assigned. The management interface will be discovered on the device based on the IP address provided.

> By default, the plugin is using the credentials defined in the main `configuration.py` for Napalm (`NAPALM_USERNAME`/`NAPALM_PASSWORD`). It's possible to define specific credentials for each onboarding task.

### Consult the status of onboarding tasks

The status of the onboarding process for each device is maintained is a dedicated table in NetBox and can be retrived :
- Via the UI `/plugins/onboarding/`
- Via the API `GET /api/plugins​/onboarding​/onboarding​/`

### API

The plugin includes 4 API endpoints to manage the onbarding tasks

```shell
GET        /api/plugins​/onboarding​/onboarding​/       Check status of all onboarding tasks.
POST    ​   /api/plugins​/onboarding​/onboarding​/       Onboard a new device
GET     ​   /api/plugins​/onboarding​/onboarding​/{id}​/  Check the status of a specific onboarding task
DELETE    ​ /api/plugins​/onboarding​/onboarding​/{id}​/  Delete a specific onboarding task
```

## Contributing

Pull requests are welcomed and automatically built and tested against multiple version of Python and multiple version of NetBox through TravisCI.

The project is packaged with a light development environment based on `docker-compose` to help with the local development of the project and to run the tests within TravisCI.

The project is following Network to Code software development guideline and is leveraging:
- Black, Pylint, Bandit and pydocstyle for Python linting and formatting.
- Django unit test to ensure the plugin is working properly.

### CLI Helper Commands

The project is coming with a CLI helper based on [invoke](http://www.pyinvoke.org/) to help setup the development environment. The commands are listed below in 3 categories `dev environment`, `utility` and `testing`. 

Each command can be executed with `invoke <command>`. All commands support the arguments `--netbox-ver` and `--python-ver` if you want to manually define the version of Python and NetBox to use. Each command also has its own help `invoke <command> --help`

#### Local dev environment
```
  build            Build all docker images.
  debug            Start NetBox and its dependencies in debug mode.
  destroy          Destroy all containers and volumes.
  start            Start NetBox and its dependencies in detached mode.
  stop             Stop NetBox and its dependencies.
```

#### Utility 
```
  cli              Launch a bash shell inside the running NetBox container.
  create-user      Create a new user in django (default: admin), will prompt for password.
  makemigrations   Run Make Migration in Django.
  nbshell          Launch a nbshell session.
```
#### Testing 

```
  tests            Run all tests for this plugin.
  pylint           Run pylint code analysis.
  pydocstyle       Run pydocstyle to validate docstring formatting adheres to NTC defined standards.
  bandit           Run bandit to validate basic static code security analysis.
  black            Run black to check that Python files adhere to its style standards.
  unittest         Run Django unit tests for the plugin.
```

## Questions

For any questions or comments, please check the [FAQ](FAQ.md) first and feel free to swing by the [Network to Code slack channel](https://networktocode.slack.com/) (channel #networktocode).
Sign up [here](http://slack.networktocode.com/)

## Screenshots

List of Onboarding Tasks
![Onboarding Tasks](docs/images/onboarding_tasks_view.png)

CSV form to import multiple devices
![CSV Form](docs/images/csv_import_view.png)

Onboard a single device
![Single Device Form](docs/images/single_device_form.png)

Menu 
![Menu](docs/images/menu.png)

